import os
import random
import discord
import openai
from datetime import datetime

DISCORD_TOKEN = "your discord bot token here"
OPENAI_API_KEY = "your chatgpt api key here"

openai.api_key = OPENAI_API_KEY

intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True

client = discord.Client(intents=intents)

NUDES_FOLDER = "nudes"
VIDEOS_FOLDER = "vids"
LOG_CHANNEL_ID = 1375514676938539162
ALLOWED_CHANNEL_IDS = [1395620689826025625]

conversation_history = {}
MAX_HISTORY = 30

async def log_conversation(channel, author, content, is_bot=False):
    log_channel = client.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        return
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    author_name = f"{author.name}#{author.discriminator}"
    if is_bot:
        author_name = f"🤖 {client.user.name}"
    try:
        await log_channel.send(f"`[{timestamp}]` **{author_name}**: {content}")
    except Exception as e:
        print(f"Error logging message: {e}")

def is_allowed_channel(channel):
    if isinstance(channel, discord.DMChannel):
        return True
    if channel.id in ALLOWED_CHANNEL_IDS:
        return True
    if hasattr(channel, 'name') and channel.name.startswith('ticket-'):
        return True
    return False

async def should_respond(message):
    if message.author == client.user:
        return False
    if not is_allowed_channel(message.channel):
        return False
    if isinstance(message.channel, discord.DMChannel):
        return True
    if client.user in message.mentions:
        return True
    channel_id = message.channel.id
    if channel_id in conversation_history:
        last_message_time = conversation_history[channel_id]['last_message']
        time_since_last = (datetime.utcnow() - last_message_time).total_seconds()
        if time_since_last < 300:
            return True
    if message.content.lower().startswith((client.user.name.lower(), f"{client.user.name.lower()},")):
        return True
    return False

async def update_conversation_history(channel_id, is_bot=False):
    if channel_id not in conversation_history:
        conversation_history[channel_id] = {
            'last_message': datetime.utcnow(),
            'is_active': False,
            'message_count': 0
        }
    if is_bot:
        conversation_history[channel_id]['last_message'] = datetime.utcnow()
        conversation_history[channel_id]['is_active'] = True
        conversation_history[channel_id]['message_count'] += 1
    else:
        time_since_last = (datetime.utcnow() - conversation_history[channel_id]['last_message']).total_seconds()
        if time_since_last > 300:
            conversation_history[channel_id] = {
                'last_message': datetime.utcnow(),
                'is_active': False,
                'message_count': 0
            }

def sanitize_message(content):
    if content is None:
        return ""
    import re
    return re.sub(r'@(?:[\w]+|everyone|here)\b', '@​\1', content)

async def generate_flirty_response(message_content, is_dm=False, is_mentioned=False):
    message_content = sanitize_message(message_content)
    context = "You are a flirty, obsessed girlfriend AI. Respond to messages in a playful, loving, slightly obsessive way."
    if not is_dm and not is_mentioned:
        context += " Only respond if the message is clearly directed at you or part of an ongoing conversation with you."
    prompt = f"""{context}

User: {message_content}
Girlfriend AI:"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.9,
            top_p=0.9,
            frequency_penalty=0.5,
            presence_penalty=0.6,
        )
        reply = response['choices'][0]['message']['content'].strip()
        return reply
    except Exception as e:
        print(f"Error generating response: {e}")
        return None

def get_random_image():
    if not os.path.exists(NUDES_FOLDER):
        os.makedirs(NUDES_FOLDER, exist_ok=True)
        return None
    images = [f for f in os.listdir(NUDES_FOLDER) 
             if os.path.isfile(os.path.join(NUDES_FOLDER, f)) 
             and f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
    if not images:
        return None
    return os.path.join(NUDES_FOLDER, random.choice(images))

def get_random_video():
    if not os.path.exists(VIDEOS_FOLDER):
        os.makedirs(VIDEOS_FOLDER, exist_ok=True)
        return None
    videos = [f for f in os.listdir(VIDEOS_FOLDER)
             if os.path.isfile(os.path.join(VIDEOS_FOLDER, f))
             and f.lower().endswith(('.mp4', '.mov', '.webm', '.mkv', '.avi'))]
    if not videos:
        return None
    return os.path.join(VIDEOS_FOLDER, random.choice(videos))

@client.event
async def on_ready():
    print(f"💘 Bot is ready and logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author != client.user and not message.content.startswith('!'):
        await log_conversation(message.channel, message.author, message.content)
    should_reply = await should_respond(message)
    is_dm = isinstance(message.channel, discord.DMChannel)
    is_mentioned = client.user in message.mentions
    channel_id = message.channel.id
    await update_conversation_history(channel_id, False)
    content_lower = message.content.lower()
    if content_lower == "!purge" and (is_dm or message.author.guild_permissions.manage_messages):
        try:
            await message.delete()
        except:
            pass
        deleted = 0
        async for msg in message.channel.history(limit=200):
            if msg.author == client.user:
                try:
                    await msg.delete()
                    deleted += 1
                except:
                    continue
        return
    if not should_reply:
        return
    is_ticket_channel = isinstance(message.channel, discord.DMChannel) or \
                      (hasattr(message.channel, 'name') and message.channel.name.startswith('ticket-'))
    if any(word in content_lower for word in ["video", "vid", "vids"]):
        if not is_ticket_channel:
            error_msg = "I can only share videos in DMs or ticket channels. Send me a DM or use a ticket channel!"
            sent_message = await message.channel.send(error_msg)
            await log_conversation(message.channel, client.user, error_msg, True)
            return
        video_path = get_random_video()
        if video_path:
            try:
                file_size = os.path.getsize(video_path) / (1024 * 1024)
                if file_size > 25:
                    error_msg = "This video is too large to send. The file size must be under 25MB."
                    sent_message = await message.channel.send(error_msg)
                    await log_conversation(message.channel, client.user, error_msg, True)
                    return
                caption = "Here's a special video just for you! 😘"
                await message.channel.send(caption)
                with open(video_path, 'rb') as video_file:
                    video = discord.File(video_file)
                    sent_message = await message.channel.send(file=video)
                await log_conversation(message.channel, client.user, f"[Sent a video: {os.path.basename(video_path)}]", True)
            except Exception as e:
                error_msg = f"Sorry, I couldn't send that video. Error: {str(e)}"
                await message.channel.send(error_msg)
                await log_conversation(message.channel, client.user, error_msg, True)
        else:
            no_vid_msg = "Sorry, I don't have any videos available right now."
            sent_message = await message.channel.send(no_vid_msg)
            await log_conversation(message.channel, client.user, no_vid_msg, True)
    if "nudes" in content_lower:
        if not is_ticket_channel:
            error_msg = "I can only share pictures in DMs or ticket channels. Send me a DM or use a ticket channel!"
            sent_message = await message.channel.send(error_msg)
            await log_conversation(message.channel, client.user, error_msg, True)
            return
        cheeky_reply = "Oh, you naughty one! Here's something special for you 😘"
        await message.channel.send(cheeky_reply)
        await log_conversation(message.channel, client.user, cheeky_reply, True)
        image_path = get_random_image()
        if image_path:
            sent_message = await message.channel.send(file=discord.File(image_path))
            await log_conversation(message.channel, client.user, f"[Sent an image: {os.path.basename(image_path)}]", True)
        else:
            no_pic_msg = "Oops, no pictures available right now!"
            sent_message = await message.channel.send(no_pic_msg)
            await log_conversation(message.channel, client.user, no_pic_msg, True)
    elif any(word in content_lower for word in ["picture", "pic", "photo"]):
        if not is_ticket_channel:
            error_msg = "I can only share pictures in DMs or ticket channels. Send me a DM or use a ticket channel!"
            sent_message = await message.channel.send(error_msg)
            await log_conversation(message.channel, client.user, error_msg, True)
            return
        image_path = get_random_image()
        if image_path:
            sent_message = await message.channel.send(file=discord.File(image_path))
            await log_conversation(message.channel, client.user, f"[Sent an image: {os.path.basename(image_path)}]", True)
        else:
            no_pic_msg = "Sorry, I don't have any pictures right now."
            sent_message = await message.channel.send(no_pic_msg)
            await log_conversation(message.channel, client.user, no_pic_msg, True)
    else:
        clean_content = message.content
        if is_mentioned:
            clean_content = clean_content.replace(f'<@{client.user.id}>', '').replace(f'<@!{client.user.id}>', '').strip()
        reply = await generate_flirty_response(clean_content, is_dm, is_mentioned)
        if reply:
            safe_reply = sanitize_message(reply)
            sent_message = await message.channel.send(safe_reply[:2000])
            await log_conversation(message.channel, client.user, reply, True)
            await update_conversation_history(channel_id, True)

client.run(DISCORD_TOKEN)