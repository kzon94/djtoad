import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp as youtube_dl
from ytmusicapi import YTMusic
import asyncio

# Cargar variables de entorno desde el archivo .env
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Configurar el bot de Discord con los intents necesarios
intents = discord.Intents.default()
intents.message_content = True  # Necesario para recibir el contenido de los mensajes
bot = commands.Bot(command_prefix="!", intents=intents)

# Inicializar YTMusic y el diccionario para las colas de reproducción
yt = YTMusic()
queues = {}  # Diccionario para las colas de reproducción por servidor

# Función para obtener una lista de canciones recomendadas
def get_song_list(song_id, exclude_song_id=None):
    recommendations = yt.get_watch_playlist(song_id)['tracks']
    recommended_songs = []
    for track in recommendations:
        if 'videoId' in track:
            video_id = track['videoId']
            if video_id != exclude_song_id:
                title = track.get('title', 'Sin título')
                recommended_songs.append((video_id, title))
            if len(recommended_songs) >= 10:
                break
    return recommended_songs

# Función para conectar al canal de voz del usuario
async def connect_to_voice(ctx):
    if not ctx.author.voice:
        await ctx.send("❌ Debes estar en un canal de voz. Croak!")
        return None
    voice_channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        return await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
        return await ctx.voice_client.move_to(voice_channel)
    return ctx.voice_client

# Función para obtener la URL y el título de un video de YouTube
async def fetch_audio_info(video_id):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        data = await asyncio.to_thread(youtube_dl.YoutubeDL(ydl_opts).extract_info, url, download=False)
        return data['url'], data.get('title', 'Sin título')
    except Exception as e:
        return None, f"❌ Error obteniendo audio: {e}, croak!"

# Función para reproducir la siguiente canción en la cola
async def play_next_song(ctx):
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        video_id, title = queues[ctx.guild.id].pop(0)
        url, _ = await fetch_audio_info(video_id)
        if not url:
            await ctx.send(f"❌ Error al obtener el audio para {title}, croak!")
            return await play_next_song(ctx)
        vc = ctx.voice_client
        vc.play(discord.FFmpegPCMAudio(url), after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(ctx), bot.loop))
        vc.source.title = title
        await ctx.send(f"🎶 Reproduciendo: {title}, croak!")
    else:
        await ctx.send("🚫 No hay más canciones en la cola. Desconectando... Croak!")
        if ctx.voice_client:
            await ctx.voice_client.disconnect()

@bot.command()
async def play(ctx, *, song_name):
    vc = await connect_to_voice(ctx)
    if not vc:
        return
    await ctx.send(f"🔍 Buscando '{song_name}' y canciones recomendadas... Croak!")
    search_results = yt.search(song_name, filter='songs')
    if not search_results or 'videoId' not in search_results[0]:
        await ctx.send("❌ No se encontraron resultados, croak!")
        return
    song_id = search_results[0]['videoId']
    url, title = await fetch_audio_info(song_id)
    if not url:
        await ctx.send(title)
        return
    if vc.is_playing():
        vc.stop()
    vc.play(discord.FFmpegPCMAudio(url), after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(ctx), bot.loop))
    vc.source.title = title
    await ctx.send(f"🎶 Reproduciendo: {title}, croak!")
    recommended_songs = get_song_list(song_id, exclude_song_id=song_id)
    queues[ctx.guild.id] = recommended_songs

@bot.command()
async def dance1(ctx):
    """Envía un GIF de baile."""
    gif_url = "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExNGQweHk5MmpidXJrZDJidzcwbGR6ZzFpZTE1ZzFuMGs3emtwOHFmaSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/pBDzxTAYdL6wRRdNTR/giphy.gif"
    await ctx.send(gif_url)

@bot.command()
async def dance2(ctx):
    """Envía otro GIF de baile."""
    gif_url = "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExaHBvc3h4ZmlqeWRhNmY1Y2wyaHFrY29jb3M1aDdpdjB6M3QzaWc3ciZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/gmUM6ag84nFnwaumx8/giphy.gif"
    await ctx.send(gif_url)

@bot.event
async def on_ready():
    print(f'✅ Tu rana favorita conectada como {bot.user}')

bot.run(DISCORD_TOKEN)
