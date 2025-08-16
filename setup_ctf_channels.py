import discord
from discord.ext import commands
import requests
from dotenv import load_dotenv
import os
import shutil

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

CTF_NAME = get_ctf_name()
print(f"[SPY_CAT] Nom CTF récupéré : {CTF_NAME}")

@bot.event
async def on_ready():
    print(f"[SPY_CAT] Connecté en tant que {bot.user}")

    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        print("[SPY_CAT] Guild non trouvée.")
        return

    root_category = discord.utils.get(guild.categories, name=CTF_NAME)
    if root_category is None:
        root_category = await guild.create_category(CTF_NAME)
        print(f"[SPY_CAT] Catégorie principale créée : {CTF_NAME}")

    # Salon général pour discuter
    general_channel = discord.utils.get(root_category.text_channels, name="general")
    if general_channel is None:
        general_channel = await guild.create_text_channel("general", category=root_category)
        await general_channel.send(f"👋 Bienvenue sur **{CTF_NAME}** !")
        print(f"[SPY_CAT] Salon général créé.")

    # Salon vocal unique
    if not discord.utils.get(root_category.voice_channels, name="Voice"):
        await guild.create_voice_channel("Voice", category=root_category)
        print("[SPY_CAT] Salon vocal créé.")

    clean_temp()
    challenges = get_challenges()
    print(f"[SPY_CAT] {len(challenges)} défis trouvés.")

    for chal in challenges:
        detail = get_challenge_detail(chal['id'])
        chal_name = f"{detail.get('category', 'Divers')}-{detail.get('name', 'unknown')}".replace(" ", "-").lower()
        description = detail.get('description', '*Pas de description.*')
        files = detail.get('files', [])

        # Crée un canal texte dédié pour le challenge
        if discord.utils.get(root_category.text_channels, name=chal_name):
            continue

        channel = await guild.create_text_channel(chal_name, category=root_category)

        embed = discord.Embed(
            title=f"{detail.get('category', '')} - {detail.get('name', '')}",
            description=description,
            color=discord.Color.green()
        )

        files_to_send = []
        for f_url in files:
            try:
                if f_url.startswith("/"):
                    full_url = f"{CTFD_URL}{f_url}"
                else:
                    full_url = f_url

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

        await channel.send(embed=embed, files=files_to_send)

    clean_temp()
    print("[SPY_CAT] Terminé.")
    await bot.close()

bot.run(DISCORD_TOKEN)