import discord
from discord.ext.commands import Bot
from discord import app_commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
CANAL_ID = 717521046642622508

intents = discord.Intents.default()
bot = Bot(command_prefix="!", intents=intents)
tree = bot.tree
scheduler = AsyncIOScheduler()

@bot.event
async def on_ready():
    if not scheduler.running:
        scheduler.start()
    await tree.sync()
    print(f"✅ Bot conectado como {bot.user}")


@tree.command(name="lembrete", description="Agende lembretes diários até a data escolhida")
@app_commands.describe(
    data="Data final do lembrete no formato DD/MM/AAAA",
    titulo="Título do lembrete",
    mensagem="Mensagem complementar"
)
async def lembrete(interaction: discord.Interaction, data: str, titulo: str, mensagem: str):
    try:
        data_lembrete = datetime.strptime(data, '%d/%m/%Y')
        hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if data_lembrete < hoje:
            await interaction.response.send_message("❌ A data precisa ser no futuro.", ephemeral=True)
            return

        canal = bot.get_channel(CANAL_ID)
        if not canal:
            await interaction.response.send_message("❌ Canal não encontrado.", ephemeral=True)
            return

        dias = (data_lembrete - hoje).days

        for i in range(dias + 1):
            data_envio = hoje + timedelta(days=i)
            hora_envio = data_envio.replace(hour=22, minute=19, second=0)

            if i == dias:
                conteudo = f"📢 Lembrete Diário! **{titulo}**\n🎲 {mensagem}\nHOJE!!"
            elif i == dias - 1:
                conteudo = f"📢 Lembrete Diário! **{titulo}**\n🎲 {mensagem}\nAMANHÃ!"
            else:
                faltam = dias - i
                conteudo = f"📢 Lembrete Diário! **{titulo}**\n🎲 {mensagem}\nFaltam {faltam} dia{'s' if faltam > 1 else ''}!"

            scheduler.add_job(
                lambda msg=conteudo: asyncio.create_task(canal.send(msg)),
                trigger='date',
                run_date=hora_envio
            )

        await interaction.response.send_message(
            f"✅ Lembretes diários agendados até {data_lembrete.strftime('%d/%m/%Y')} com o título: '{titulo}'",
            ephemeral=False
        )

    except ValueError:
        await interaction.response.send_message("❌ Data inválida. Use o formato DD-MM-AAAA", ephemeral=True)


@tree.command(name="testar_mensagem", description="Envia uma mensagem de teste agora")
@app_commands.describe(
    titulo="Título da mensagem de teste",
    mensagem="Mensagem complementar"
)
async def testar_mensagem(interaction: discord.Interaction, titulo: str, mensagem: str):
    canal = bot.get_channel(CANAL_ID)
    if canal:
        conteudo = f"📢 Lembrete Diário! **{titulo}**\n🎲 {mensagem}\n(mensagem de teste)"
        await canal.send(conteudo)
        await interaction.response.send_message("✅ Mensagem enviada!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Canal não encontrado.", ephemeral=True)


bot.run(TOKEN)
