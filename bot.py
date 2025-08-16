import os
import random

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import pandas as pd
from discord.ext.commands import has_permissions, CheckFailure
# CONFIG 

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv("GUILD_ID"))

intents = discord.Intents.default()
intents.message_content = True

# Emoji 
def random_cat():
    return random.choice([
        "<:cat3:1389433164987891712>",
        "<:cat4:1389433163868274719>",
        "<:cat5:1389433162685218878>",
        "<:cat6:1389433161632579664>",
        "<:cat7:1389433160382550186>",
        "<:cat8:1389433158436519967>",
        "<:cat9:1389433155915616256>",
        "<:cat10:1389433165940265021>"
    ])

spycat_X = "<:spycat_X:1390091541472612482>"
spycat_good = "<:spycat_good:1390091537219584112>"
spycat_hint = "<:spycat_hint:1390091535336603728>"
spycat_roulette = "<:spycat_roulette:1390091539270598728>"
spycat_roulette_hit = "<:spycat_roulette_hit:1390091533457293322>"
spycat_roulette_miss = "<:spycat_roulette_miss:1390091530861023363>"
spycat_stop = "<:spycat_stop:1390091528717991946>"

# UTILS 

def check_flag_in_csv(flag: str):
    df = pd.read_csv('valid_flags.csv')
    row = df[df['Flag'] == flag]
    if not row.empty:
        points = int(row['Points'].values[0])
        return True, points
    else:
        return False, 0



def update_scoreboard(user: str, flag: str, points: int) -> bool:
    df = pd.read_csv('scoreboard.csv')

    if user not in df['Team'].values:
        new_row = pd.DataFrame([{
            'Team': user,
            'Points': points,
            'Submitted_Flags': flag
        }])
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        idx = df.index[df['Team'] == user][0]
        submitted_flags = str(df.at[idx, 'Submitted_Flags'])
        if pd.isna(submitted_flags) or submitted_flags == 'nan':
            submitted_flags = ""

        flags = [f.strip() for f in submitted_flags.split(';') if f.strip()]
        if flag in flags:
            return False  
        df.at[idx, 'Points'] += points
        flags.append(flag)
        df.at[idx, 'Submitted_Flags'] = ';'.join(flags)

    df.to_csv('scoreboard.csv', index=False)
    return True


# BOT

class SpyCatBot(commands.Bot):
    def __init__(self):

        super().__init__(command_prefix="/", intents=intents)
        self.synced = False

    async def setup_hook(self):

        for g in self.guilds:
            try:
                self.tree.copy_global_to(guild=discord.Object(id=g.id))
                await self.tree.sync(guild=discord.Object(id=g.id))
                print(f"[SPY_CAT] Slash commands sync -> {g.name} ({g.id})")
            except Exception as e:
                print(f"[SPY_CAT] Sync failed for {g.id}: {e}")

        try:
            await self.tree.sync()
            print("[SPY_CAT] Global commands synced (may take time to propagate).")
        except Exception as e:
            print(f"[SPY_CAT] Global sync failed: {e}")

bot = SpyCatBot()

@bot.event
async def on_guild_join(guild: discord.Guild):
    """Quand le bot rejoint un nouveau serveur, pousse immédiatement les slash commands dedans."""
    try:
        bot.tree.copy_global_to(guild=discord.Object(id=guild.id))
        await bot.tree.sync(guild=discord.Object(id=guild.id))
        print(f"[SPY_CAT] Joined {guild.name} -> commands synced.")
    except Exception as e:
        print(f"[SPY_CAT] Sync on join failed for {guild.id}: {e}")




@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if "CSIUL{" in message.content:
        try:
            await message.delete()
        except discord.Forbidden:
            print("[SPY_CAT] Permission refusée pour supprimer un message.")

        try:
            await message.channel.send(
                f"{spycat_stop} Chhht agent {message.author.mention} ! "
                f"SpyCat a intercepté ton flag `{message.content.strip()[:30]}...` "
                f"et l’a réduit en cendres. "
                f"Les secrets ne miaulent pas en plein jour. {spycat_X}",
                delete_after=5
            )
        except discord.Forbidden:
            print("[SPY_CAT] Impossible d'envoyer une alerte.")

    await bot.process_commands(message)


# EVENTS

@bot.event
async def on_ready():
    print(f'[SPY_CAT] Bot connecté en tant que {bot.user}')


# COMMANDS

## SCOREBOARD 
@bot.tree.command(name="scoreboard", description="Affiche le classement des agents.")
async def scoreboard(interaction: discord.Interaction):
    df = pd.read_csv('scoreboard.csv')
    df = df.sort_values(by='Points', ascending=False).reset_index(drop=True)

    msg = f"**{spycat_good} SPYCAT SCOREBOARD {spycat_good}**\n```"

    for index, row in df.iterrows():
        rank = index + 1
        team = row['Team']
        points = row['Points']
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
        msg += f"{medal} {team.ljust(15)} {str(points).rjust(5)} pts\n"

    msg += "```"

    await interaction.response.send_message(msg)



## WHOAMI 
@bot.tree.command(name="whoami", description="Affiche tes points actuels.")
async def whoami(interaction: discord.Interaction):
    df = pd.read_csv('scoreboard.csv')
    user = interaction.user.name

    if user in df['Team'].values:
        idx = df.index[df['Team'] == user][0]
        points = df.at[idx, 'Points']
        submitted = df.at[idx, 'Submitted_Flags']
        submitted = submitted if pd.notna(submitted) else "Aucun flag soumis"
    else:
        points = 0
        submitted = "Aucun flag soumis"

    await interaction.response.send_message(
        f"🐾 Agent {user} : {points} pts. Flags trouvés : {submitted} {random_cat()}"
    )


## STATS
@bot.tree.command(name="stats", description="Stats globales des agents.")
async def stats(interaction: discord.Interaction):
    df = pd.read_csv('scoreboard.csv')
    nb_teams = len(df)
    total_points = df['Points'].sum()
    await interaction.response.send_message(
        f"{spycat_hint} **Statistiques du Réseau SpyCat** {spycat_hint}\n"
        f"👥 Agents actifs : **{nb_teams}**\n"
        f"💰 Total de points volés : **{total_points}**\n"
        f"{spycat_good} Continue de traquer, espion !"
    )


## CAT 
@bot.tree.command(name="cat", description="Miaou aléatoire pour l'ambiance.")
async def cat(interaction: discord.Interaction):
    await interaction.response.send_message(f"{random_cat()} Miaou ~ {random_cat()}")


## SUBMIT
@bot.tree.command(name="submit", description="Soumets ton flag à ta planque secrète.")
@app_commands.describe(flag="Ton flag à soumettre")
async def submit(interaction: discord.Interaction, flag: str):
    guild = interaction.guild
    user = interaction.user
    channel_name = f"planque-{user.name}".lower()

    planque = discord.utils.get(guild.text_channels, name=channel_name)

    if interaction.channel.name == channel_name:
        is_valid, points = check_flag_in_csv(flag)

        if is_valid:
            added = update_scoreboard(user.name, flag, points)
            if added:
                result_msg = (
                    f"{spycat_good} Bien joué agent **{user.name}** !\n"
                    f"Ton flag est **correct** (+{points} pts) !"
                )
            else:
                result_msg = (
                    f"{spycat_stop} Agent **{user.name}**, ce flag est correct "
                    f"mais déjà soumis ! Aucun point ajouté."
                )
        else:
            result_msg = (
                f"{spycat_X} Désolé agent **{user.name}**, "
                f"ce flag est **incorrect** ! Essaie encore !"
            )

        await interaction.response.send_message(
            f"🔑 Flag soumis : `{flag}`\n{result_msg}"
        )
    else:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        category = discord.utils.get(guild.categories, name="Planques")

        if planque is None:
            planque = await guild.create_text_channel(
                channel_name, overwrites=overwrites, category=category
            )

        await planque.send(
            f"📬 Flag reçu : `{flag}` Bien planqué ici.\n"
            f"{spycat_stop} Pour vérifier, soumets-le à nouveau **dans cette planque** !"
        )
        await interaction.response.send_message(
            f"📬 Flag reçu ! Vérifie ta planque secrète : {planque.mention} {spycat_stop}",
            ephemeral=True
        )


## HELP
@bot.tree.command(name="help", description="Affiche le manuel de l'espion SPY_CAT.")
async def help_command(interaction: discord.Interaction):
    help_msg = f"""
**📖 GUIDE DE L'AGENT SPY_CAT {spycat_hint}**

Voici tes outils, espion 🐾 :

{spycat_hint} **/scoreboard**
   Classement complet des espions et points volés.

{spycat_hint} **/whoami**
   Vérifie combien de points tu as volé toi-même.

{spycat_hint} **/stats**
   Stats globales pour tous les agents sous couverture.

{spycat_hint} **/challenge**
   Reçois ton flag de départ, encodé en base64.

{spycat_hint} **/cat**
   Un miaulement aléatoire pour l’ambiance d’espionnage.

{spycat_stop} Les flags hors planque sont interceptés et détruits sur-le-champ.
Reste dans l’ombre, agent. Miaou ! {spycat_X}
"""
    await interaction.response.send_message(help_msg)



# LEGACY COMMANDS

@bot.command(name='delete_category')
@has_permissions(administrator=True)
async def delete_category(ctx, *, category_name: str):
    """Supprime une catégorie CTF et tous ses salons (admin seulement)"""
    category = discord.utils.get(ctx.guild.categories, name=category_name)
    if not category:
        await ctx.send(
            f"{spycat_X} Catégorie introuvable : **{category_name}**",
            delete_after=5
        )
        return

    for channel in category.channels:
        await channel.delete()
    await category.delete()
    await ctx.send(
        f"{spycat_good} Catégorie **{category_name}** et ses salons ont été supprimés.",
        delete_after=5
    )



@delete_category.error
async def delete_category_error(ctx, error):
    if isinstance(error, CheckFailure):
        await ctx.send(
            f"{spycat_stop} Chhht ! Tu n’as pas la permission d’utiliser cette commande. *(Admin seulement)*",
            delete_after=5
        )

        
## SOLVED
@bot.tree.command(name="solved", description="Marque ce challenge comme résolu (Forum ou Thread).")
async def solved(interaction: discord.Interaction):
    thread = interaction.channel

    if not isinstance(thread, discord.Thread):
        await interaction.response.send_message(
            f"{spycat_stop} Cette commande doit être utilisée dans un **thread** !",
            ephemeral=True
        )
        return

    parent = thread.parent

    if isinstance(parent, discord.ForumChannel):
        solved_tag = discord.utils.get(parent.available_tags, name="✅ Solved")
        unsolved_tag = discord.utils.get(parent.available_tags, name="❌ Unsolved")

        tags = [tag for tag in thread.applied_tags if tag.name != "❌ Unsolved"]

        if solved_tag and solved_tag not in tags:
            tags.append(solved_tag)

        new_name = thread.name
        if not new_name.startswith("✅ "):
            new_name = f"✅ {new_name.lstrip('❌ ').strip()}"

        await thread.edit(applied_tags=tags, name=new_name)

        await interaction.response.send_message(
            f"{spycat_good} Challenge marqué comme **Résolu** (Forum) : `{new_name}`",
            ephemeral=False
        )

    else:
        if not thread.name.startswith("✅ "):
            new_name = f"✅ {thread.name.lstrip('❌ ').strip()}"
            await thread.edit(name=new_name)
            await interaction.response.send_message(
                f"{spycat_good} Challenge marqué comme **Résolu** : `{new_name}`",
                ephemeral=False
            )
        else:
            await interaction.response.send_message(
                f"{spycat_stop} Ce challenge est déjà marqué comme **Résolu**.",
                ephemeral=True
            )





@bot.tree.command(name="letsfuckingo", description="Marque ce challenge comme résolu et renomme le thread.")
async def letsfuckingo(interaction: discord.Interaction):
    thread = interaction.channel

    if not isinstance(thread, discord.Thread):
        await interaction.response.send_message(
            f"{spycat_stop} Pas ici, agent ! Cette commande s’utilise dans un **thread** — SpyCat ne veut pas voir ça ailleurs.",
            ephemeral=True
        )
        return

    parent = thread.parent

    if isinstance(parent, discord.ForumChannel):
        solved_tag = discord.utils.get(parent.available_tags, name="✅ Solved")
        unsolved_tag = discord.utils.get(parent.available_tags, name="❌ Unsolved")

        tags = [tag for tag in thread.applied_tags if tag.name != "❌ Unsolved"]
        if solved_tag and solved_tag not in tags:
            tags.append(solved_tag)

        new_name = thread.name
        if not new_name.startswith("✅ "):
            new_name = f"✅ {new_name.lstrip('❌ ').strip()}"
            await thread.edit(applied_tags=tags, name=new_name)
        else:
            await thread.edit(applied_tags=tags)

        await interaction.response.send_message(
                                        """``` 

                ░█─── █▀▀ ▀▀█▀▀ █ █▀▀ 　 █▀▀ █──█ █▀▀ █─█ ─▀─ █▀▀▄ █▀▀▀ 　 █▀▀▀ █▀▀█ 
                ░█─── █▀▀ ──█── ─ ▀▀█ 　 █▀▀ █──█ █── █▀▄ ▀█▀ █──█ █─▀█ 　 █─▀█ █──█ 
                ░█▄▄█ ▀▀▀ ──▀── ─ ▀▀▀ 　 ▀── ─▀▀▀ ▀▀▀ ▀─▀ ▀▀▀ ▀──▀ ▀▀▀▀ 　 ▀▀▀▀ ▀▀▀▀
                ```"""
            f"{spycat_good} 🎉 SpyCat bondit sur sa chaise, claque sa patte et marque ce thread comme **RÉSOLU** : `{new_name}`.\n"
            f"🕵️‍⬛ *Prochaine traque ? SpyCat est prêt, ses moustaches frétillent d’excitation.*",
            ephemeral=False
        )

    else:
        if not thread.name.startswith("✅ "):
            new_name = f"✅ {thread.name.lstrip('❌ ').strip()}"
            await thread.edit(name=new_name)
            await interaction.response.send_message(
                            """``` 

                ░█─── █▀▀ ▀▀█▀▀ █ █▀▀ 　 █▀▀ █──█ █▀▀ █─█ ─▀─ █▀▀▄ █▀▀▀ 　 █▀▀▀ █▀▀█ 
                ░█─── █▀▀ ──█── ─ ▀▀█ 　 █▀▀ █──█ █── █▀▄ ▀█▀ █──█ █─▀█ 　 █─▀█ █──█ 
                ░█▄▄█ ▀▀▀ ──▀── ─ ▀▀▀ 　 ▀── ─▀▀▀ ▀▀▀ ▀─▀ ▀▀▀ ▀──▀ ▀▀▀▀ 　 ▀▀▀▀ ▀▀▀▀
                ```"""
                f"{spycat_good} 🎉 SpyCat crie victoire et note : Challenge **RÉSOLU** → `{new_name}`.\n"
                f"🥳 *Une mission de plus, un mystère de moins.*",
                ephemeral=False
            )
        else:
            await interaction.response.send_message(
                f"{spycat_stop} SpyCat grogne : ce challenge est déjà **RÉSOLU** !",
                ephemeral=True
            )


@bot.tree.command(name="enfintabarnak", description="Marque ce challenge comme résolu et renomme le thread.")
async def enfintabarnak(interaction: discord.Interaction):
    thread = interaction.channel

    if not isinstance(thread, discord.Thread):
        await interaction.response.send_message(
            f"{spycat_stop} T’es pas dans un thread, agent ! SpyCat ne veut pas voir ça ailleurs.",
            ephemeral=True
        )
        return

    parent = thread.parent

    if isinstance(parent, discord.ForumChannel):
        solved_tag = discord.utils.get(parent.available_tags, name="✅ Solved")
        unsolved_tag = discord.utils.get(parent.available_tags, name="❌ Unsolved")

        tags = [tag for tag in thread.applied_tags if tag.name != "❌ Unsolved"]
        if solved_tag and solved_tag not in tags:
            tags.append(solved_tag)

        new_name = thread.name
        if not new_name.startswith("✅ "):
            new_name = f"✅ {new_name.lstrip('❌ ').strip()}"
            await thread.edit(applied_tags=tags, name=new_name)
        else:
            await thread.edit(applied_tags=tags)

        await interaction.response.send_message(
            """``` 
            ███████╗███╗░░██╗███████╗██╗███╗░░██╗  ████████╗░█████╗░██████╗░░█████╗░██████╗░███╗░░██╗░█████╗░██╗░░██╗
            ██╔════╝████╗░██║██╔════╝██║████╗░██║  ╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔══██╗████╗░██║██╔══██╗██║░██╔╝
            █████╗░░██╔██╗██║█████╗░░██║██╔██╗██║  ░░░██║░░░███████║██████╦╝███████║██████╔╝██╔██╗██║███████║█████═╝░
            ██╔══╝░░██║╚████║██╔══╝░░██║██║╚████║  ░░░██║░░░██╔══██║██╔══██╗██╔══██║██╔══██╗██║╚████║██╔══██║██╔═██╗░
            ███████╗██║░╚███║██║░░░░░██║██║░╚███║  ░░░██║░░░██║░░██║██████╦╝██║░░██║██║░░██║██║░╚███║██║░░██║██║░╚██╗
            ╚══════╝╚═╝░░╚══╝╚═╝░░░░░╚═╝╚═╝░░╚══╝  ░░░╚═╝░░░╚═╝░░╚═╝╚═════╝░╚═╝░░╚═╝╚═╝░░╚═╝╚═╝░░╚══╝╚═╝░░╚═╝╚═╝░░╚═╝
            ```"""
            f"{spycat_good} SpyCat bondit sur ton clavier, pousse un *miaulement de victoire* et raye ce défi de sa liste noire : `{new_name}`.\n"
            f"🐾 *Une ride de plus, une griffe de moins — mais la chasse continue.*",
            ephemeral=False
        )

    else:
        if not thread.name.startswith("✅ "):
            new_name = f"✅ {thread.name.lstrip('❌ ').strip()}"
            await thread.edit(name=new_name)
            await interaction.response.send_message(
                """``` 
                ███████╗███╗░░██╗███████╗██╗███╗░░██╗  ████████╗░█████╗░██████╗░░█████╗░██████╗░███╗░░██╗░█████╗░██╗░░██╗
                ██╔════╝████╗░██║██╔════╝██║████╗░██║  ╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔══██╗████╗░██║██╔══██╗██║░██╔╝
                █████╗░░██╔██╗██║█████╗░░██║██╔██╗██║  ░░░██║░░░███████║██████╦╝███████║██████╔╝██╔██╗██║███████║█████═╝░
                ██╔══╝░░██║╚████║██╔══╝░░██║██║╚████║  ░░░██║░░░██╔══██║██╔══██╗██╔══██║██╔══██╗██║╚████║██╔══██║██╔═██╗░
                ███████╗██║░╚███║██║░░░░░██║██║░╚███║  ░░░██║░░░██║░░██║██████╦╝██║░░██║██║░░██║██║░╚███║██║░░██║██║░╚██╗
                ╚══════╝╚═╝░░╚══╝╚═╝░░░░░╚═╝╚═╝░░╚══╝  ░░░╚═╝░░░╚═╝░░╚═╝╚═════╝░╚═╝░░╚═╝╚═╝░░╚═╝╚═╝░░╚══╝╚═╝░░╚═╝╚═╝░░╚═╝
                ```"""
                f"{spycat_good} 🎉 SpyCat déchire le dernier indice et hurle : *Mission accomplie.* `{new_name}` est **RÉSOLU**.\n"
                f"✨ *Va prendre tes croquettes, tu l’as mérité.*",
                ephemeral=False
            )
        else:
            await interaction.response.send_message(
                f"{spycat_stop} Trop tard agent : ce challenge est déjà **RÉSOLU** — SpyCat ricane dans l’ombre.",
                ephemeral=True
            )


## UNSOLVED
@bot.tree.command(name="unsolved", description="Marque ce challenge comme non résolu (Forum ou Thread).")
async def unsolved(interaction: discord.Interaction):
    thread = interaction.channel

    if not isinstance(thread, discord.Thread):
        await interaction.response.send_message(
            f"{spycat_stop} Cette commande doit être utilisée dans un **thread**, espion !",
            ephemeral=True
        )
        return

    parent = thread.parent

    if isinstance(parent, discord.ForumChannel):
        solved_tag = discord.utils.get(parent.available_tags, name="✅ Solved")
        unsolved_tag = discord.utils.get(parent.available_tags, name="❌ Unsolved")

        tags = [tag for tag in thread.applied_tags if tag.name != "✅ Solved"]

        if unsolved_tag and unsolved_tag not in tags:
            tags.append(unsolved_tag)

        clean_name = thread.name.lstrip('✅❌ ').strip()

        await thread.edit(applied_tags=tags, name=clean_name)
        await interaction.response.send_message(
            f"{spycat_X} Le challenge est maintenant marqué comme **Non Résolu** (Forum) : `{clean_name}`.\n"
            f"🐾 SpyCat garde un œil... Réessaye de le griffer !",
            ephemeral=False
        )

    else:
        clean_name = thread.name.lstrip('✅❌ ').strip()

        await thread.edit(name=clean_name)
        await interaction.response.send_message(
            f"{spycat_X} Le challenge est maintenant marqué comme **Non Résolu** : `{clean_name}`.\n"
            f"{spycat_hint} *SpyCat t’observe, prêt pour un nouvel assaut.*",
            ephemeral=False
        )


## CHALLENGES LIST
@bot.tree.command(name="challenges", description="Affiche la liste des challenges disponibles (Planque Only).")
async def challenges(interaction: discord.Interaction):
    guild = interaction.guild
    user = interaction.user
    channel_name = f"planque-{user.name}".lower()
    planque = discord.utils.get(guild.text_channels, name=channel_name)

    if interaction.channel.name != channel_name:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        category = discord.utils.get(guild.categories, name="Planques")
        if planque is None:
            planque = await guild.create_text_channel(
                channel_name, overwrites=overwrites, category=category
            )

        await planque.send(
            f"{spycat_hint} Utilise `/challenges` **dans ta planque** : {planque.mention} {spycat_stop}"
        )
        await interaction.response.send_message(
            f"{spycat_stop} Seuls les agents tapis dans leur planque peuvent consulter la liste : {planque.mention}",
            ephemeral=True
        )
        return

    msg = f"""
**{spycat_hint} Dossier Classifié : Challenges Disponibles**

Voici ta liste, petit espion 👀 :
{spycat_hint}

 `/first_claw` : La première trace laissée par SpyCat. Débute ta traque.
 `/spycat_hideout` : Tente de forcer la tanière secrète de SpyCat.
 `/terminal` : Fouille le terminal HoneyPaw pour trouver des fichiers suspects.
 `/last_paw` : La dernière trace... mais SpyCat a 8 vies. Jusqu'où iras-tu ?
 `/hint challenge:<nom>` : Tente la roulette russe pour un indice... si tu oses.

**{spycat_X} Tous ces challenges ne fonctionnent que dans ta planque secrète !**
Si tu agis hors de l’ombre, SpyCat dévore tes espoirs.

Bonne traque, agent. Et surveille tes moustaches. {spycat_hint}
"""
    await interaction.response.send_message(msg)




## Hint Command
@bot.tree.command(name="hint", description="Tente ta chance pour un hint de SpyCat (Planque Only).")
@app_commands.describe(challenge="Nom du challenge pour le hint.")
async def hint(interaction: discord.Interaction, challenge: str):
    guild = interaction.guild
    user = interaction.user
    channel_name = f"planque-{user.name}".lower()

    planque = discord.utils.get(guild.text_channels, name=channel_name)

    if interaction.channel.name != channel_name:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        category = discord.utils.get(guild.categories, name="Planques")
        if planque is None:
            planque = await guild.create_text_channel(
                channel_name, overwrites=overwrites, category=category
            )

        await planque.send(
            f"{spycat_hint} Essaie `/hint challenge:{challenge}` ici pour obtenir ton indice ! {spycat_stop}"
        )
        await interaction.response.send_message(
            f"{spycat_stop} Va dans ta planque pour demander un hint : {planque.mention}",
            ephemeral=True
        )
        return
    
    HINTS = {
        "first_claw": [
            f"{spycat_roulette_hit} SpyCat murmure : *Regarde bien ces symboles... Un langage bien connu des pirates du Net.*",
            f"{spycat_roulette_hit} SpyCat s’étire : *Décoder n’est que le début. Soumettre est une autre histoire.*",
            f"{spycat_roulette_hit} SpyCat griffe : *Le flag est déjà sous ton nez. Sais-tu seulement le lire ?*",
            f"{spycat_roulette_miss} SpyCat se gratte l’oreille. Aucun indice pour toi aujourd’hui.",
            f"{spycat_roulette_miss} Un miaulement sarcastique résonne. Reviens plus tard."
        ],
        "spycat_hideout": [
            f"{spycat_roulette_hit} SpyCat glisse : *L’adresse n’est jamais ce qu’elle paraît être.*",
            f"{spycat_roulette_hit} SpyCat ronronne : *64 façons de cacher un secret...* ",
            f"{spycat_roulette_hit} SpyCat feule : *Des chiffres qui veulent devenir des lettres...* ",
            f"{spycat_roulette_hit} SpyCat ricane : *Un décalage bien placé peut renverser un empire.*",
            
            f"{spycat_roulette_miss} SpyCat baille. Rien pour toi aujourd'hui.",
            f"{spycat_roulette_miss} Mauvais jeton. Essaie encore, petit curieux.",
            f"{spycat_roulette_miss} Mes moustaches frémissent : pas d’indice pour toi.",
            f"{spycat_roulette_miss} Trop curieux ? Reviens quand tu sauras vraiment griffer."
        ],
        "terminal": [
            f"{spycat_hint} SpyCat ricane : *Toutes les pattes mènent au Honeypaw... mais certaines griffures cachent mieux que d’autres.*",
            f"{spycat_hint} SpyCat feule : *Ne t’arrête pas au premier fichier. Pousse tes griffes plus loin...*",
            f"{spycat_hint} SpyCat ronronne : *Un répertoire peut cacher un autre. Creuse.*",
            f"{spycat_roulette_miss} Tes pattes sont trop molles pour mériter un indice.",
            f"{spycat_roulette_miss} SpyCat ferme ses yeux. Pas aujourd’hui."
        ],
        "last_paw": [
            f"{spycat_roulette_hit} SpyCat griffe : *Les métadonnées murmurent des secrets que tes yeux n’ont jamais lus...* ",
            f"{spycat_roulette_hit} SpyCat ronronne : *Un simple fichier peut cacher une tanière plus profonde qu’il n’y paraît...* ",
            f"{spycat_roulette_hit} SpyCat ricane : *Fouille jusqu’à la moelle. Même ce que tu crois inutile peut miauler un indice.* ",
            f"{spycat_roulette_hit} SpyCat feule : *Croise tes griffes : commentaires, cachettes, chaînes perdues... parfois tout se rejoint.*",
            f"{spycat_roulette_miss} SpyCat baille : *Pas d’indice. Cherche encore, petit curieux.*",
            f"{spycat_roulette_miss} SpyCat lève la queue : *Un miaulement moqueur. Tu n’as rien aujourd’hui.*",
            f"{spycat_roulette_miss} SpyCat ferme ses yeux : *Reviens quand tes pattes seront plus affutées.*",
            f"{spycat_roulette_miss} SpyCat s’enfuit dans l’ombre : *Pas d’indice. Pour l’instant.*"
        ]
    }

    if challenge not in HINTS:
        await interaction.response.send_message(
            f"{spycat_X} Aucun hint pour ce challenge : `{challenge}`",
            ephemeral=True
        )
        return

    chosen = random.choice(HINTS[challenge])
    await interaction.response.send_message(
        f"{spycat_roulette} Roulette russe de SpyCat pour **{challenge}** :\n{chosen} {spycat_roulette}"
    )

## Challenge de départ
@bot.tree.command(name="first_claw", description="Pose ta première griffe sur le flag de départ (Planque Only).")
async def first_claw(interaction: discord.Interaction):
    guild = interaction.guild
    user = interaction.user
    channel_name = f"planque-{user.name}".lower()
    planque = discord.utils.get(guild.text_channels, name=channel_name)

    if interaction.channel.name != channel_name:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        category = discord.utils.get(guild.categories, name="Planques")
        if planque is None:
            planque = await guild.create_text_channel(
                channel_name, overwrites=overwrites, category=category
            )

        await planque.send(
            f"{spycat_stop} Essaie `/challenge` ici pour commencer ta traque : {planque.mention} {spycat_stop}"
        )
        await interaction.response.send_message(
            f"{spycat_stop} Commande réservée à ta planque : {planque.mention}",
            ephemeral=True
        )
        return

    base64_flag = "Q1NJVUx7U3B5Q2F0X2lzX3dhdGNoaW5nX3lvdX0="
    msg = (
        """``` 

   ▄████████  ▄█     ▄████████    ▄████████     ███           ▄████████  ▄█          ▄████████  ▄█     █▄  
  ███    ███ ███    ███    ███   ███    ███ ▀█████████▄      ███    ███ ███         ███    ███ ███     ███ 
  ███    █▀  ███▌   ███    ███   ███    █▀     ▀███▀▀██      ███    █▀  ███         ███    ███ ███     ███ 
 ▄███▄▄▄     ███▌  ▄███▄▄▄▄██▀   ███            ███   ▀      ███        ███         ███    ███ ███     ███ 
▀▀███▀▀▀     ███▌ ▀▀███▀▀▀▀▀   ▀███████████     ███          ███        ███       ▀███████████ ███     ███ 
  ███        ███  ▀███████████          ███     ███          ███    █▄  ███         ███    ███ ███     ███ 
  ███        ███    ███    ███    ▄█    ███     ███          ███    ███ ███▌    ▄   ███    ███ ███ ▄█▄ ███ 
  ███        █▀     ███    ███  ▄████████▀     ▄████▀        ████████▀  █████▄▄██   ███    █▀   ▀███▀███▀  
                    ███    ███                                          ▀                                  

        ```"""
        f"**{spycat_hint} Chasse au Chat : Première Griffe {spycat_hint}**\n"
        f"Miaou~ Agent {user.name}, tu crois vraiment pouvoir effleurer ma patte ?\n"
        f"SpyCat t’observe derrière chaque ligne de code… Et ce n’est que le début.\n\n"
        f"🔑 **Clé cryptée** : `{base64_flag}`\n"
        f"Décode, gratte, et reviens miauler.\n"
        f"Bonne traque, petit humain… et n’oublie pas : SpyCat n’est jamais loin. {random_cat()}\n\n"
    )
    await interaction.response.send_message(msg)

## SpyCat Hideout Challenge
@bot.tree.command(name="spycat_hideout", description="Tente de découvrir la planque secrète de SpyCat.")
async def spycat_hideout(interaction: discord.Interaction):
    guild = interaction.guild
    user = interaction.user
    channel_name = f"planque-{user.name}".lower()
    planque = discord.utils.get(guild.text_channels, name=channel_name)

    if interaction.channel.name != channel_name:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        category = discord.utils.get(guild.categories, name="Planques")
        if planque is None:
            planque = await guild.create_text_channel(
                channel_name, overwrites=overwrites, category=category
            )

        await planque.send(
            f"{spycat_stop} Commande `/spycat_hideout` réservée à ta planque ! Essaie ici : {planque.mention} {spycat_stop}"
        )
        await interaction.response.send_message(
            f"{spycat_stop} Pas ici ! Va dans ta planque : {planque.mention}",
            ephemeral=True
        )
        return

    lore_msg =f"""
{spycat_hint} **Dossier Classifié : SpyCat Hideout**

*Bienvenue, espion {user.name}…*

Tu te tiens à la porte de ma tanière.  
SpyCat n’ouvre qu’à ceux qui savent lire entre les griffures.

Ce que je cache n’est pas protégé par un simple cadenas :  
ici, chaque couche est une ruse, chaque caractère un piège.

Certains se perdent dans des encodages futiles,  
d’autres croient qu’un simple coup de patte suffira.  
**Ils ont tous échoué.**

Rappelle-toi :  
> *Celui qui me trouve n’a plus rien à prouver à personne.*

Quand tu croiras être digne, apporte-moi ta preuve :

NDYgNTYgNGMgNTggNGYgN2IgNzcgNmIgNjggNWYgNzcgNzUgNzggNjggNWYgNmIgNmMgNjcgNjggNzIgNzggNzcgNWYgNzIgNjkgNWYgNzYgNzMgNjIgNjYgNjQgNzcgNWYgNmMgNzYgNWYgNzIgNzEgNmYgNjIgNWYgNjkgNzIgNzUgNWYgNzcgNmIgNjggNWYgNzYgNmIgNjQgNzUgNzMgNjggNzYgNzcgNWYgNjQgNmEgNjggNzEgNzcgNzYgN2Q%3D

{spycat_roulette} *Si ta patte tremble,* murmure `/hint challenge:spycat_hideout`  
… mais sache que ma roulette n’a pas de pitié pour les faibles.

{spycat_hint}
"""
    await interaction.response.send_message(lore_msg)



## SpyCat Terminal Challenge 
@bot.tree.command(name="terminal", description="Simule un terminal Linux piégé par SpyCat.")
@app_commands.describe(cmd="Commande à exécuter (ls, pwd, cat <file>, ls ..)")
async def terminal(interaction: discord.Interaction, cmd: str):
    guild = interaction.guild
    user = interaction.user
    channel_name = f"planque-{user.name}".lower()
    planque = discord.utils.get(guild.text_channels, name=channel_name)

    if interaction.channel.name != channel_name:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        category = discord.utils.get(guild.categories, name="Planques")
        if planque is None:
            planque = await guild.create_text_channel(
                channel_name, overwrites=overwrites, category=category
            )

        await planque.send(
            f"{spycat_stop} SpyCat a ouvert un terminal… mais uniquement dans ta planque : {planque.mention} {spycat_stop}"
        )
        await interaction.response.send_message(
            f"{spycat_stop} Utilise `/terminal` seulement dans ta planque : {planque.mention}",
            ephemeral=True
        )
        return

    cmd = cmd.strip().lower()
    output = ""

    if cmd == "pwd":
        output = "/secret_hideout/HoneyPaw"
    elif cmd == "ls":
        output = "flag.txt spycat_is_watching_you.txt"
    elif cmd.startswith("cat "):
        file = cmd.split(" ", 1)[1]
        if file == "flag.txt":
            output = (
                f"😹 Bien tenté, espion en carton ! "
                f"Ce flag est plus vide qu’un bol de croquettes à 3h du matin.\n"
                f"*Réfléchis, ou SpyCat te regardera échouer encore.*"
            )
        elif file == "spycat_is_watching_you.txt":
            output = (
                """
                ░██████╗██████╗░██╗░░░██╗░█████╗░░█████╗░████████╗  ░██╗░░░░░░░██╗░█████╗░░██████╗  ██╗░░██╗███████╗██████╗░███████╗
                ██╔════╝██╔══██╗╚██╗░██╔╝██╔══██╗██╔══██╗╚══██╔══╝  ░██║░░██╗░░██║██╔══██╗██╔════╝  ██║░░██║██╔════╝██╔══██╗██╔════╝
                ╚█████╗░██████╔╝░╚████╔╝░██║░░╚═╝███████║░░░██║░░░  ░╚██╗████╗██╔╝███████║╚█████╗░  ███████║█████╗░░██████╔╝█████╗░░
                ░╚═══██╗██╔═══╝░░░╚██╔╝░░██║░░██╗██╔══██║░░░██║░░░  ░░████╔═████║░██╔══██║░╚═══██╗  ██╔══██║██╔══╝░░██╔══██╗██╔══╝░░
                ██████╔╝██║░░░░░░░░██║░░░╚█████╔╝██║░░██║░░░██║░░░  ░░╚██╔╝░╚██╔╝░██║░░██║██████╔╝  ██║░░██║███████╗██║░░██║███████╗
                ╚═════╝░╚═╝░░░░░░░░╚═╝░░░░╚════╝░╚═╝░░╚═╝░░░╚═╝░░░  ░░░╚═╝░░░╚═╝░░╚═╝░░╚═╝╚═════╝░  ╚═╝░░╚═╝╚══════╝╚═╝░░╚═╝╚══════╝

                """
            )
        elif file == "../secret_flag.txt":
            output = "CSIUL{SpyCat_Loves_HoneyPaws}"
        else:
            output = f"cat: {file}: Aucun fichier ou dossier de ce type"
    elif cmd == "ls ..":
        output = "secret_flag.txt"
    else:
        output = f" Commande inconnue : `{cmd}`. SpyCat ricane dans l’ombre."

    await interaction.response.send_message(
        f"```bash\n$ {cmd}\n{output}\n```"
    )

@bot.tree.command(name="last_paw", description="Commence ta traque avec la première empreinte de SpyCat.")
async def last_paw(interaction: discord.Interaction):
    user = interaction.user.name

    msg =f"""
**{spycat_hint} Dossier Ultra-Confidentiel : Première Griffe de SpyCat {spycat_hint}**

🐾 *Agent {user}, tu as osé poser ta patte sur ma trace...*

> *Regarde au-delà des pixels...*  
> *Lis entre les griffures EXIF...*

Dans chaque octet, je laisse une empreinte :  
- 🗂️ Un champ de **commentaire** peut devenir un tunnel.
- 🧩 Un mot-clé peut devenir une clé.

Quand tu déchiffreras ce que je cache,  
rapporte-le **dans ta planque**... et seulement là.

Miaou~ Espion. 🕵️‍⬛ {random_cat()}
"""
    file = discord.File("SpyCatIsWatchingYou.jpg", filename="SpyCatIsWatchingYou.jpg")
    await interaction.response.send_message(msg, file=file)



# RUN 

bot.run(DISCORD_TOKEN)
