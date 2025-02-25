#
#   DJTOAD V1.0 - Para ejecución en local o VPS via VM Google Cloud o similar
#

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
            # Limitar a 10 canciones
            if len(recommended_songs) >= 10:
                break
    return recommended_songs

# Función para conectar al canal de voz del usuario
async def connect_to_voice(ctx):
    if not ctx.author.voice:
        await ctx.send("❌ Debes estar en un canal de voz. ¡Croak!")
        return None

    voice_channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        return await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
        return await ctx.voice_client.move_to(voice_channel)
    return ctx.voice_client

# Función para obtener la URL y el título de un video de YouTube
async def fetch_audio_info(video_id):
    """Obtiene la información del audio antes de reproducirlo."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        data = await asyncio.to_thread(
            youtube_dl.YoutubeDL(ydl_opts).extract_info,
            url,
            download=False
        )
        return data['url'], data.get('title', 'Sin título')
    except Exception as e:
        return None, f"❌ Error obteniendo audio: {e}. ¡Croak!"

# Función para reproducir la siguiente canción en la cola
async def play_next_song(ctx, attempts=0):
    MAX_ATTEMPTS = 3
    if attempts >= MAX_ATTEMPTS:
        await ctx.send("❌ No se pudo reproducir la siguiente canción. ¡Croak!")
        return
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        video_id, title = queues[ctx.guild.id].pop(0)
        url, _ = await fetch_audio_info(video_id)
        if not url:
            await ctx.send(f"❌ Error al obtener el audio para {title}. ¡Croak!")
            return await play_next_song(ctx, attempts + 1)  # Intentar la siguiente canción

        vc = ctx.voice_client

        def after_playing(error):
            fut = asyncio.run_coroutine_threadsafe(
                play_next_song(ctx), bot.loop
            )
            try:
                fut.result()
            except Exception as e:
                print(f"Error en after_playing: {e}")

        vc.play(discord.FFmpegPCMAudio(url), after=after_playing)
        vc.source.title = title  # Guardar el título de la canción actual
        await ctx.send(f"🎶 Reproduciendo: {title}. ¡Croak!")
    else:
        await ctx.send("🚫 No hay más canciones en la cola. Desconectando... ¡Croak!")
        if ctx.voice_client:
            await ctx.voice_client.disconnect()

# Comando '!play' para reproducir una canción
@bot.command()
async def play(ctx, *, song_name):
    vc = await connect_to_voice(ctx)
    if not vc:
        return

    await ctx.send(f"🔍 Buscando '{song_name}' y canciones recomendadas... ¡Croak!")

    # Buscar la canción y obtener su ID
    search_results = yt.search(song_name, filter='songs')
    if not search_results or 'videoId' not in search_results[0]:
        await ctx.send("❌ No se encontraron resultados. ¡Croak!")
        return
    song_id = search_results[0]['videoId']

    # Obtener la URL y el título de la canción
    url, title = await fetch_audio_info(song_id)
    if not url:
        await ctx.send(title)  # Mensaje de error
        return

    if vc.is_playing():
        vc.stop()

    def after_playing(error):
        fut = asyncio.run_coroutine_threadsafe(
            play_next_song(ctx), bot.loop
        )
        try:
            fut.result()
        except Exception as e:
            print(f"Error en after_playing: {e}")

    vc.play(discord.FFmpegPCMAudio(url), after=after_playing)
    vc.source.title = title  # Guardar el título de la canción actual
    await ctx.send(f"🎶 Reproduciendo: {title}. ¡Croak!")

    # Obtener canciones recomendadas y actualizar la cola
    await ctx.send("⏳ Obteniendo canciones recomendadas... ¡Croak!")
    recommended_songs = get_song_list(song_id, exclude_song_id=song_id)
    queues[ctx.guild.id] = recommended_songs
    await ctx.send("✅ Lista de reproducción descargada exitosamente. ¡Croak!")

# Comando '!add' para añadir una canción al inicio de la cola
@bot.command()
async def add(ctx, *, song_name):
    """Añade una canción al inicio de la cola de reproducción."""
    await ctx.send(f"🔍 Buscando '{song_name}' en YouTube Music... ¡Croak!")

    # Buscar la canción
    search_results = yt.search(song_name, filter='songs')
    if not search_results or 'videoId' not in search_results[0]:
        await ctx.send("❌ No se encontraron resultados. ¡Croak!")
        return
    song_id = search_results[0]['videoId']
    title = search_results[0].get('title', 'Sin título')

    # Verificar si existe una cola de reproducción para el servidor actual
    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = []

    # Añadir la canción al inicio de la cola
    queues[ctx.guild.id].insert(0, (song_id, title))
    await ctx.send(f"✅ '{title}' ha sido añadida al inicio de la cola de reproducción. ¡Croak!")

# Comando '!next' para saltar a la siguiente canción
@bot.command()
async def next(ctx):
    """Salta a la siguiente canción en la cola."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Saltando a la siguiente canción... ¡Croak!")
    else:
        await ctx.send("🚫 No hay una canción reproduciéndose actualmente. ¡Croak!")

# Comando '!list' para mostrar la cola de reproducción actual
@bot.command()
async def list(ctx):
    """Muestra la canción actual y la lista de canciones en la cola de reproducción."""
    message = ""
    vc = ctx.voice_client
    if vc and vc.is_playing() and hasattr(vc.source, 'title'):
        current_song = vc.source.title
        message += f"🎶 **Canción sonando:** {current_song}\n\n"
    else:
        message += "ℹ️ **No hay una canción reproduciéndose actualmente. ¡Croak!**\n\n"

    if ctx.guild.id in queues and queues[ctx.guild.id]:
        message += "**🎵 Cola de reproducción:**\n"
        for index, (video_id, title) in enumerate(queues[ctx.guild.id], start=1):
            message += f"{index}. {title}\n"
    else:
        message += "ℹ️ La cola de reproducción está vacía. ¡Croak!"

    await ctx.send(message)

# Comando '!pause' para pausar la reproducción
@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Reproducción pausada. ¡Croak!")
    else:
        await ctx.send("🚫 No hay una canción reproduciéndose para pausar. ¡Croak!")

# Comando '!resume' para reanudar la reproducción
@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Reproducción reanudada. ¡Croak!")
    else:
        await ctx.send("🚫 No hay una canción pausada para reanudar. ¡Croak!")

# Comando '!stop' para detener la reproducción y desconectar al bot
@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        queues.pop(ctx.guild.id, None)
        await ctx.send("⏹️ Bot desconectado y cola borrada. ¡Croak!")
    else:
        await ctx.send("🚫 No estoy conectado a un canal de voz. ¡Croak!")

# Comando '!dance1' para enviar un GIF de baile
@bot.command()
async def dance1(ctx):
    """Envía un divertido GIF de baile."""
    gif_url = "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExNGQweHk5MmpidXJrZDJidzcwbGR6ZzFpZTE1ZzFuMGs3emtwOHFmaSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/pBDzxTAYdL6wRRdNTR/giphy.gif"
    await ctx.send(gif_url)
    await ctx.send("💃 ¡A bailar! ¡Croak!")

# Comando '!dance2' para enviar otro GIF de baile
@bot.command()
async def dance2(ctx):
    """Envía otro divertido GIF de baile."""
    gif_url = "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExaHBvc3h4ZmlqeWRhNmY1Y2wyaHFrY29jb3M1aDdpdjB6M3QzaWc3ciZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/gmUM6ag84nFnwaumx8/giphy.gif"
    await ctx.send(gif_url)
    await ctx.send("🕺 ¡Que siga la fiesta! ¡Croak!")

# Evento cuando el bot está listo
@bot.event
async def on_ready():
    print(f'✅ Tu rana favorita conectada como {bot.user}')

# Ejecutar el bot
bot.run(DISCORD_TOKEN)
