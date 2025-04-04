import os
import sys
import random
import asyncio
import json
import logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import InputPeerChannel, InputPeerUser, InputPeerChat
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError, ChannelInvalidError, ChannelPrivateError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_ID = 28645630  # Replace with your API ID
API_HASH = '11d53ff5e45d145e65ebcb0618b2e3a9'  # Replace with your API Hash
SESSION_NAME = 'userbot_session_y'
CONFIG_FILE = 'userbot_config.json'

# Default configuration
config = {
    'admin_id': None,
    'target_chat_id': None,
    'group_list': [],
    'delay': 300,  # 5 minutes default
    'is_running': False
}

# Initialize the client
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# Load configuration
def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        logger.info("Configuration loaded successfully")
    else:
        logger.info("No configuration file found, using default settings")
        save_config()

# Save configuration
def save_config():
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
    logger.info("Configuration saved successfully")

# Check if user is admin
def is_admin(user_id):
    return str(user_id) == str(config['admin_id'])

# Format time from seconds
def format_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {seconds}s"

# Helper to ensure all required settings are set
def check_settings_complete():
    required = ['admin_id', 'target_chat_id', 'group_list', 'delay']
    for setting in required:
        if setting not in config or config[setting] is None:
            if setting == 'group_list' and config[setting] == []:
                return False, f"Daftar grup kosong. Tambahkan grup dengan .addgrup"
            return False, f"Setting '{setting}' belum diatur. Gunakan perintah yang sesuai untuk mengaturnya."
    
    if not config['group_list']:
        return False, "Daftar grup kosong. Tambahkan grup dengan .addgrup"
    
    return True, "Semua pengaturan sudah lengkap"

# Helper function to safely get entity
async def safe_get_entity(entity_id):
    if entity_id is None:
        return None
    
    try:
        # Try with provided ID
        return await client.get_entity(entity_id)
    except ValueError:
        try:
            # Try with int conversion
            return await client.get_entity(int(entity_id))
        except Exception as e:
            logger.error(f"Error getting entity: {str(e)}")
            return None
    except Exception as e:
        logger.error(f"Error getting entity: {str(e)}")
        return None

# Helper function to safely send message
async def safe_send_message(recipient_id, message):
    if recipient_id is None:
        return None
    
    try:
        # First try to get the entity
        entity = await safe_get_entity(recipient_id)
        if entity:
            return await client.send_message(entity, message)
        else:
            # If entity not found, try direct ID
            return await client.send_message(recipient_id, message)
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return None

# Forward message operation
async def forward_random_message():
    if not config['is_running']:
        return
    
    try:
        # Randomly select a source group
        if not config['group_list']:
            await safe_send_message(config['admin_id'], "❌ Tidak ada grup sumber yang tersedia!")
            config['is_running'] = False
            save_config()
            return
        
        source_group = random.choice(config['group_list'])
        
        # Get the last 50 messages from the source group
        messages = []
        try:
            source_entity = await safe_get_entity(source_group)
            if not source_entity:
                await safe_send_message(config['admin_id'], f"❌ Tidak dapat menemukan grup sumber: {source_group}")
                if config['is_running']:
                    loop = asyncio.get_event_loop()
                    loop.create_task(schedule_next_forward())
                return
            
            async for message in client.iter_messages(source_entity, limit=50):
                if message.media or message.text:  # Only consider messages with media or text
                    messages.append(message)
        except Exception as e:
            await safe_send_message(config['admin_id'], f"❌ Error mengakses grup sumber: {str(e)}")
            if config['is_running']:
                loop = asyncio.get_event_loop()
                loop.create_task(schedule_next_forward())
            return
        
        if not messages:
            await safe_send_message(config['admin_id'], f"⚠️ Tidak menemukan pesan yang dapat diteruskan dari: {source_group}")
            if config['is_running']:
                loop = asyncio.get_event_loop()
                loop.create_task(schedule_next_forward())
            return
        
        # Choose a random message
        chosen_message = random.choice(messages)
        
        # Get target entity
        target_entity = await safe_get_entity(config['target_chat_id'])
        if not target_entity:
            await safe_send_message(config['admin_id'], f"❌ Tidak dapat menemukan target chat: {config['target_chat_id']}")
            if config['is_running']:
                loop = asyncio.get_event_loop()
                loop.create_task(schedule_next_forward())
            return
        
        # Forward or copy the message to target chat
        try:
            if chosen_message.media:
                sent_message = await client.send_file(
                    target_entity,
                    file=chosen_message.media,
                    caption=chosen_message.text if chosen_message.text else None
                )
                media_type = "Audio" if chosen_message.audio else "Video" if chosen_message.video else "Photo" if chosen_message.photo else "File"
                message_info = f"{media_type} dengan caption: {chosen_message.text[:50]}..." if chosen_message.text else f"{media_type} tanpa caption"
            else:
                sent_message = await client.send_message(
                    target_entity,
                    chosen_message.text
                )
                message_info = f"Text: {chosen_message.text[:50]}..." if chosen_message.text and len(chosen_message.text) > 50 else f"Text: {chosen_message.text}"
            
            # Send report to admin
            time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            source_name = getattr(source_entity, 'title', str(source_group))
            target_name = getattr(target_entity, 'title', str(config['target_chat_id']))
            
            report = f"✅ Pesan berhasil dikirim!\n\n" \
                    f"⏰ Waktu: {time_now}\n" \
                    f"📤 Dari: {source_name}\n" \
                    f"📥 Ke: {target_name}\n" \
                    f"📄 Jenis: {message_info}\n" \
                    f"⏱️ Delay: {format_time(config['delay'])}"
            
            await safe_send_message(config['admin_id'], report)
        except Exception as e:
            await safe_send_message(config['admin_id'], f"❌ Error saat mengirim pesan: {str(e)}")
        
        # Schedule next forwarding
        if config['is_running']:
            loop = asyncio.get_event_loop()
            loop.create_task(schedule_next_forward())
    
    except FloodWaitError as e:
        await safe_send_message(
            config['admin_id'], 
            f"⚠️ Terkena flood wait. Menunggu {e.seconds} detik sebelum mencoba lagi."
        )
        # Pause for the flood wait time, then resume
        await asyncio.sleep(e.seconds)
        if config['is_running']:
            loop = asyncio.get_event_loop()
            loop.create_task(schedule_next_forward())
    
    except (ChannelInvalidError, ChannelPrivateError) as e:
        await safe_send_message(
            config['admin_id'], 
            f"❌ Error: Tidak dapat mengakses channel/grup. Detail: {str(e)}"
        )
        if config['is_running']:
            loop = asyncio.get_event_loop()
            loop.create_task(schedule_next_forward())
    
    except Exception as e:
        await safe_send_message(
            config['admin_id'], 
            f"❌ Error saat mengirim pesan: {str(e)}"
        )
        if config['is_running']:
            loop = asyncio.get_event_loop()
            loop.create_task(schedule_next_forward())

async def schedule_next_forward():
    await asyncio.sleep(config['delay'])
    if config['is_running']:
        await forward_random_message()

# Command handlers
@client.on(events.NewMessage(pattern=r'\.settarget(?:\s+(.+))?'))
async def set_target_command(event):
    if not is_admin(event.sender_id):
        return
    
    # If parameter is provided, try to use it as a username/link
    if event.pattern_match.group(1):
        input_text = event.pattern_match.group(1).strip()
        
        try:
            # Try to join the group/channel if not already a member
            try:
                entity = await client.get_entity(input_text)
                if hasattr(entity, 'username') and entity.username:
                    try:
                        await client(JoinChannelRequest(entity))
                        await event.respond(f"✅ Berhasil bergabung dengan {entity.title}")
                    except Exception as e:
                        # Might already be a member, continue anyway
                        pass
            except Exception as e:
                await event.respond(f"⚠️ Tidak dapat bergabung: {str(e)}")
                return
            
            # Get entity after potentially joining
            entity = await client.get_entity(input_text)
            config['target_chat_id'] = entity.id
            save_config()
            await event.respond(f"✅ Target chat berhasil diatur ke '{entity.title}'!")
            
        except Exception as e:
            await event.respond(f"❌ Error: {str(e)}")
    
    # If no parameter, use current chat (original behavior)
    else:
        config['target_chat_id'] = event.chat_id
        save_config()
        await event.respond("✅ Target chat berhasil diatur ke chat ini!")

@client.on(events.NewMessage(pattern=r'\.listtarget'))
async def list_target_command(event):
    if not is_admin(event.sender_id):
        return
    
    if not config['target_chat_id']:
        await event.respond("🎯 Belum ada target yang diatur. Gunakan .settarget untuk mengatur target.")
        return
    
    entity = await safe_get_entity(config['target_chat_id'])
    if entity:
        target_info = f"🎯 Target saat ini: {getattr(entity, 'title', 'Unknown')} (ID: {config['target_chat_id']})"
    else:
        target_info = f"🎯 Target saat ini: ID: {config['target_chat_id']} (⚠️ Tidak dapat mengakses entity)"
    
    await event.respond(target_info)

@client.on(events.NewMessage(pattern=r'\.cleartarget'))
async def clear_target_command(event):
    if not is_admin(event.sender_id):
        return
    
    config['target_chat_id'] = None
    save_config()
    await event.respond("🎯 Target telah dihapus!")

@client.on(events.NewMessage(pattern=r'\.addgrup(?:\s+(.+))?'))
async def add_group_command(event):
    if not is_admin(event.sender_id):
        return
    
    # If parameter is provided, try to use it as a username/link
    if event.pattern_match.group(1):
        input_text = event.pattern_match.group(1).strip()
        
        try:
            # Try to join the group/channel if not already a member
            try:
                entity = await client.get_entity(input_text)
                if hasattr(entity, 'username') and entity.username:
                    try:
                        await client(JoinChannelRequest(entity))
                        await event.respond(f"✅ Berhasil bergabung dengan {entity.title}")
                    except Exception as e:
                        # Might already be a member, continue anyway
                        pass
            except Exception as e:
                await event.respond(f"⚠️ Tidak dapat bergabung: {str(e)}")
                return
            
            # Get entity after potentially joining
            entity = await client.get_entity(input_text)
            group_id = entity.id
            group_title = entity.title
            
            # Check if group is already in the list
            if str(group_id) in [str(g) for g in config['group_list']]:
                await event.respond(f"⚠️ Grup '{group_title}' sudah ada dalam daftar!")
                return
            
            config['group_list'].append(str(group_id))
            save_config()
            await event.respond(f"✅ Grup '{group_title}' berhasil ditambahkan ke daftar!")
            
        except Exception as e:
            await event.respond(f"❌ Error: {str(e)}")
    
    # If no parameter, use current chat (original behavior)
    elif event.is_group or event.is_channel:
        group_id = event.chat_id
        group_title = event.chat.title
        
        # Check if group is already in the list
        if str(group_id) in [str(g) for g in config['group_list']]:
            await event.respond(f"⚠️ Grup '{group_title}' sudah ada dalam daftar!")
            return
        
        config['group_list'].append(str(group_id))
        save_config()
        await event.respond(f"✅ Grup '{group_title}' berhasil ditambahkan ke daftar!")
    else:
        await event.respond("❌ Berikan username/link grup atau gunakan perintah ini di dalam grup!")

@client.on(events.NewMessage(pattern=r'\.listgrup'))
async def list_group_command(event):
    if not is_admin(event.sender_id):
        return
    
    if not config['group_list']:
        await event.respond("📋 Daftar grup kosong. Tambahkan grup dengan perintah .addgrup")
        return
    
    group_list_text = "📋 Daftar Grup:\n\n"
    for i, group_id in enumerate(config['group_list'], 1):
        entity = await safe_get_entity(group_id)
        if entity:
            group_list_text += f"{i}. {getattr(entity, 'title', 'Unknown')} (ID: {group_id})\n"
        else:
            group_list_text += f"{i}. Unknown Group (ID: {group_id}) (⚠️ Tidak dapat mengakses entity)\n"
    
    await event.respond(group_list_text)

@client.on(events.NewMessage(pattern=r'\.rmgrup (\d+)'))
async def remove_group_command(event):
    if not is_admin(event.sender_id):
        return
    
    try:
        index = int(event.pattern_match.group(1))
        if 1 <= index <= len(config['group_list']):
            removed_group_id = config['group_list'].pop(index - 1)
            save_config()
            
            entity = await safe_get_entity(removed_group_id)
            if entity:
                group_title = getattr(entity, 'title', 'Unknown')
                await event.respond(f"✅ Grup '{group_title}' berhasil dihapus dari daftar!")
            else:
                await event.respond(f"✅ Grup dengan ID {removed_group_id} berhasil dihapus dari daftar!")
        else:
            await event.respond(f"❌ Indeks tidak valid! Gunakan angka 1-{len(config['group_list'])}.")
    except ValueError:
        await event.respond("❌ Format tidak valid! Gunakan .rmgrup [nomor]")

@client.on(events.NewMessage(pattern=r'\.setdelay (\d+)'))
async def set_delay_command(event):
    if not is_admin(event.sender_id):
        return
    
    try:
        delay_seconds = int(event.pattern_match.group(1))
        if delay_seconds < 30:
            await event.respond("⚠️ Delay minimum adalah 30 detik!")
            return
        
        config['delay'] = delay_seconds
        save_config()
        
        formatted_time = format_time(delay_seconds)
        await event.respond(f"⏱️ Delay berhasil diatur ke {formatted_time}!")
    except ValueError:
        await event.respond("❌ Format tidak valid! Gunakan .setdelay [detik]")

@client.on(events.NewMessage(pattern=r'\.mulai'))
async def start_command(event):
    if not is_admin(event.sender_id):
        return
    
    # Check if all settings are complete
    complete, message = check_settings_complete()
    if not complete:
        await event.respond(f"❌ {message}")
        return
    
    if config['is_running']:
        await event.respond("⚠️ Userbot sudah berjalan!")
        return
    
    config['is_running'] = True
    save_config()
    await event.respond("✅ Userbot telah dimulai! Akan mengirim pesan sesuai delay yang diatur.")
    
    # Start the forwarding process
    loop = asyncio.get_event_loop()
    loop.create_task(forward_random_message())

@client.on(events.NewMessage(pattern=r'\.stop'))
async def stop_command(event):
    if not is_admin(event.sender_id):
        return
    
    config['is_running'] = False
    save_config()
    await event.respond("🛑 Userbot telah dihentikan!")

@client.on(events.NewMessage(pattern=r'\.setadmin'))
async def set_admin_command(event):
    # Allow setting admin if none is set, or if the command is from the current admin
    if config['admin_id'] is None or is_admin(event.sender_id):
        config['admin_id'] = event.sender_id
        save_config()
        
        # Test if we can message this admin
        try:
            entity = await client.get_entity(event.sender_id)
            await event.respond("👑 Anda telah diatur sebagai admin userbot!")
        except Exception as e:
            await event.respond(f"⚠️ Anda telah diatur sebagai admin, tetapi terjadi error saat mencoba mendapatkan entity: {str(e)}")
    else:
        # Silent ignore for non-admins
        pass

@client.on(events.NewMessage(pattern=r'\.status'))
async def status_command(event):
    if not is_admin(event.sender_id):
        return
    
    complete, _ = check_settings_complete()
    
    status_text = "📊 Status Userbot:\n\n"
    status_text += f"🤖 Status: {'Berjalan' if config['is_running'] else 'Berhenti'}\n"
    status_text += f"👑 Admin ID: {config['admin_id']}\n"
    
    # Check if admin entity can be accessed
    admin_entity = await safe_get_entity(config['admin_id'])
    if admin_entity:
        status_text += f"👤 Admin: {getattr(admin_entity, 'first_name', '')} {getattr(admin_entity, 'last_name', '')}\n"
    else:
        status_text += "⚠️ Admin entity tidak dapat diakses\n"
    
    status_text += f"🎯 Target Chat ID: {config['target_chat_id']}\n"
    
    # Check if target entity can be accessed
    if config['target_chat_id']:
        target_entity = await safe_get_entity(config['target_chat_id'])
        if target_entity:
            status_text += f"🎯 Target: {getattr(target_entity, 'title', 'Unknown')}\n"
        else:
            status_text += "⚠️ Target entity tidak dapat diakses\n"
    
    status_text += f"⏱️ Delay: {format_time(config['delay'])}\n"
    status_text += f"📋 Jumlah Grup: {len(config['group_list'])}\n"
    status_text += f"⚙️ Konfigurasi: {'Lengkap' if complete else 'Belum Lengkap'}"
    
    await event.respond(status_text)

@client.on(events.NewMessage(pattern=r'\.help'))
async def help_command(event):
    if not is_admin(event.sender_id):
        return
    
    help_text = """
📚 **Daftar Perintah Userbot**:

🔹 **.setadmin** - Mengatur pengguna sebagai admin userbot
🔹 **.settarget [username/link]** - Mengatur grup target untuk mengirim pesan
🔹 **.listtarget** - Menampilkan target yang diatur saat ini
🔹 **.cleartarget** - Menghapus pengaturan target
🔹 **.addgrup [username/link]** - Menambahkan grup ke daftar grup sumber
🔹 **.listgrup** - Menampilkan daftar grup sumber
🔹 **.rmgrup [nomor]** - Menghapus grup dari daftar berdasarkan nomor urut
🔹 **.setdelay [detik]** - Mengatur delay antar pengiriman pesan
🔹 **.mulai** - Memulai proses pengiriman pesan
🔹 **.stop** - Menghentikan proses pengiriman pesan
🔹 **.status** - Menampilkan status userbot
🔹 **.help** - Menampilkan daftar perintah ini

⚠️ **Catatan**:
- Semua pengaturan harus diatur sebelum memulai userbot
- Delay minimum adalah 30 detik
- Userbot hanya akan merespon perintah dari admin
- Anda dapat menggunakan username atau link untuk menambahkan grup/channel
"""
    await event.respond(help_text)

@client.on(events.NewMessage)
async def on_new_message(event):
    # Set the first user who interacts as admin if none is set
    if config['admin_id'] is None and event.sender_id:
        config['admin_id'] = event.sender_id
        save_config()
        await event.respond("👑 Anda telah diatur sebagai admin userbot! Ketik .help untuk melihat daftar perintah.")

# Main function
async def main():
    # Load config at startup
    load_config()
    
    # Start the client
    await client.start()
    
    logger.info("Userbot started. Waiting for commands...")
    
    # Run the client until disconnected
    await client.run_until_disconnected()

if __name__ == "__main__":
    # Run the main function
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
