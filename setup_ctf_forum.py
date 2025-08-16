import os
import shutil
import requests
import discord

from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# === === === CONFIG === === ===

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
CTFD_URL = os.getenv("CTFD_URL")
CTFD_TOKEN = os.getenv("CTFD_TOKEN")
COOKIE_SESSION = os.getenv("COOKIE_SESSION")

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

HEADERS = {
    "Authorization": f"Token {CTFD_TOKEN}",
    "Accept": "application/json",
    "Cookie": f"session={COOKIE_SESSION}"
}

# === === === UTILS === === ===

def get_challenges():
    url = f"{CTFD_URL}/api/v1/challenges"
    response = requests.get(url, headers=HEADERS)
    print(f"[DEBUG] Challenges Status: {response.status_code}")
    response.raise_for_status()
    return response.json()["data"]

def get_challenge_detail(chal_id):
    url = f"{CTFD_URL}/api/v1/challenges/{chal_id}"
    response = requests.get(url, headers=HEADERS)
    print(f"[DEBUG] Challenge {chal_id} Status: {response.status_code}")
    response.raise_for_status()
    return response.json().get("data", {})

def get_ctf_name():
    url = f"{CTFD_URL}/api/v1/configs"
    response = requests.get(url, headers=HEADERS)
    print(f"[DEBUG] Configs Status: {response.status_code}")
    response.raise_for_status()
    for item in response.json().get("data", []):
        if item.get("key") == "ctf_name":
            return item.get("value", "CTF")
    return "CTF"

def clean_temp():
    if os.path.exists("temp"):
        shutil.rmtree("temp")
    os.makedirs("temp", exist_ok=True)

# === === === BOT EVENTS === === ===

@bot.event
async def on_ready():
    print(f"[SPY_CAT] Connecté en tant que {bot.user}")

    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        print("[SPY_CAT] Guild non trouvée.")
        return

    ctf_name = get_ctf_name()
    print(f"[SPY_CAT] Nom CTF récupéré : {ctf_name}")

    root_category = discord.utils.get(guild.categories, name=ctf_name)
    if root_category is None:
        root_category = await guild.create_category(ctf_name)
        print(f"[SPY_CAT] Catégorie principale créée : {ctf_name}")

    forum_channel = discord.utils.get(
        guild.channels,
        name="challenges",
        type=discord.ChannelType.forum
    )

    if forum_channel is None:
        print("[SPY_CAT] ❌ Forum 'challenges' introuvable ! Crée-le manuellement avant de lancer le bot.")
        await bot.close()
        return

    print("[SPY_CAT] ✅ Forum 'challenges' trouvé !")

    # Liste mutable des tags actuels
    existing_tags = list(forum_channel.available_tags)

    clean_temp()
    challenges = get_challenges()
    print(f"[SPY_CAT] {len(challenges)} défis trouvés.")

    for chal in challenges:
        detail = get_challenge_detail(chal['id'])
        chal_category = detail.get('category', '').strip()
        chal_name = f"{chal_category}-{detail.get('name', 'unknown')}".replace(" ", "-").lower()
        description = detail.get('description', '*Pas de description.*')
        files = detail.get('files', [])

        if any(thread.name == chal_name for thread in forum_channel.threads):
            print(f"[SPY_CAT] Post déjà existant : {chal_name}")
            continue

        applied_tags = []

        # === Catégorie ===
        cat_tag = None

        # Vérifie en insensitive
        if any(tag.name.lower() == chal_category.lower() for tag in existing_tags):
            # Si présent, récupère l'exact avec la casse
            cat_tag = discord.utils.get(existing_tags, name=chal_category)
            if not cat_tag:
                # Sinon récupère le premier match insensible
                for tag in existing_tags:
                    if tag.name.lower() == chal_category.lower():
                        cat_tag = tag
                        break
            print(f"[SPY_CAT] ✅ Tag '{chal_category}' existe déjà (insensitive check).")
        elif chal_category:
            print(f"[SPY_CAT] ❌ Tag '{chal_category}' n'existe pas encore. Création...")
            new_tag = discord.ForumTag(name=chal_category, moderated=False)
            existing_tags.append(new_tag)

            # Dédupli stricte insensible
            seen_lower = set()
            unique_tags = []
            for t in existing_tags:
                lname = t.name.lower()
                if lname not in seen_lower:
                    unique_tags.append(t)
                    seen_lower.add(lname)
                else:
                    print(f"[SPY_CAT] ⚠️ Doublon retiré : {t.name}")

            existing_tags = unique_tags
            cat_tag = new_tag
            print(f"[SPY_CAT] Liste unique envoyée : {[t.name for t in existing_tags]}")
            await forum_channel.edit(available_tags=existing_tags)
            print(f"[SPY_CAT] ➕ Nouveau tag créé : {chal_category}")

        if cat_tag:
            applied_tags.append(cat_tag)

        # === ❌ Unsolved ===
        unsolved_tag = None
        if any(tag.name.lower() == "❌ unsolved".lower() for tag in existing_tags):
            unsolved_tag = discord.utils.get(existing_tags, name="❌ Unsolved")
            if not unsolved_tag:
                for tag in existing_tags:
                    if tag.name.lower() == "❌ unsolved".lower():
                        unsolved_tag = tag
                        break
            print("[SPY_CAT] ✅ Tag '❌ Unsolved' existe déjà (insensitive check).")
        else:
            print("[SPY_CAT] ❌ Tag '❌ Unsolved' n'existe pas encore. Création...")
            new_unsolved = discord.ForumTag(name="❌ Unsolved", moderated=False)
            existing_tags.append(new_unsolved)

            seen_lower = set()
            unique_tags = []
            for t in existing_tags:
                lname = t.name.lower()
                if lname not in seen_lower:
                    unique_tags.append(t)
                    seen_lower.add(lname)
                else:
                    print(f"[SPY_CAT] ⚠️ Doublon retiré : {t.name}")

            existing_tags = unique_tags
            unsolved_tag = new_unsolved
            print(f"[SPY_CAT] Liste unique envoyée : {[t.name for t in existing_tags]}")
            await forum_channel.edit(available_tags=existing_tags)
            print("[SPY_CAT] ➕ Nouveau tag créé : ❌ Unsolved")

        if unsolved_tag:
            applied_tags.append(unsolved_tag)

        print(f"[SPY_CAT] ✅ Tags appliqués : {[tag.name for tag in applied_tags]}")



        # === Prépare embed & fichiers ===
        embed = discord.Embed(
            title=f"{chal_category} - {detail.get('name', '')}",
            description=description,
            color=discord.Color.green()
        )

        files_to_send = []
        for f_url in files:
            try:
                full_url = f"{CTFD_URL}{f_url}" if f_url.startswith("/") else f_url
                f_name = full_url.split("/")[-1].split("?")[0]
                f_resp = requests.get(full_url, headers=HEADERS, stream=True)
                if f_resp.status_code == 200:
                    with open(f"temp/{f_name}", "wb") as f:
                        f.write(f_resp.content)
                    files_to_send.append(discord.File(f"temp/{f_name}"))
                else:
                    embed.add_field(name="📎 Fichier indisponible", value=full_url, inline=False)
            except Exception as e:
                print(f"[SPY_CAT] Erreur téléchargement fichier : {e}")

        safe_content = description.strip() or "Voir détails ci-dessous :"
        safe_embed = embed if embed.description.strip() or embed.fields else None
        safe_files = files_to_send or []

        await forum_channel.create_thread(
            name=chal_name,
            content=safe_content,
            embed=safe_embed,
            files=safe_files,
            applied_tags=applied_tags
        )

        print(f"[SPY_CAT] ✅ Post Forum créé : {chal_name}")

    clean_temp()
    print("[SPY_CAT] Posts Forum pour tous les challenges créés.")
    await bot.close()




# === === === COMMANDES POUR STATUT === === ===

@bot.tree.command(name="solved", description="Marque ce challenge comme résolu (Forum).")
async def solved(interaction: discord.Interaction):
    thread = interaction.channel

    if not isinstance(thread, discord.Thread) or not isinstance(thread.parent, discord.ForumChannel):
        await interaction.response.send_message(
            "🚫 Cette commande doit être utilisée dans un **post du Forum** !",
            ephemeral=True
        )
        return

    forum = thread.parent
    solved_tag = discord.utils.get(forum.available_tags, name="✅ Solved")
    unsolved_tag = discord.utils.get(forum.available_tags, name="❌ Unsolved")

    tags = [tag.id for tag in thread.applied_tags if tag.name != "❌ Unsolved"]
    if solved_tag and solved_tag.id not in tags:
        tags.append(solved_tag.id)

    await thread.edit(applied_tags=tags)
    await interaction.response.send_message(
        "✅ Le challenge est maintenant marqué comme **Résolu**.",
        ephemeral=False
    )

@bot.tree.command(name="unsolved", description="Marque ce challenge comme non résolu (Forum).")
async def unsolved(interaction: discord.Interaction):
    thread = interaction.channel

    if not isinstance(thread, discord.Thread) or not isinstance(thread.parent, discord.ForumChannel):
        await interaction.response.send_message(
            "🚫 Cette commande doit être utilisée dans un **post du Forum** !",
            ephemeral=True
        )
        return

    forum = thread.parent
    solved_tag = discord.utils.get(forum.available_tags, name="✅ Solved")
    unsolved_tag = discord.utils.get(forum.available_tags, name="❌ Unsolved")

    tags = [tag.id for tag in thread.applied_tags if tag.name != "✅ Solved"]
    if unsolved_tag and unsolved_tag.id not in tags:
        tags.append(unsolved_tag.id)

    await thread.edit(applied_tags=tags)
    await interaction.response.send_message(
        "🔄 Le challenge est maintenant marqué comme **Non Résolu**.",
        ephemeral=False
    )

# === === === RUN === === ===

bot.run(DISCORD_TOKEN)
