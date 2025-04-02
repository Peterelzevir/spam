import os
import json
import random
import asyncio
import logging
import getpass
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest, InviteToChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest, GetDialogsRequest, ImportChatInviteRequest
from telethon.tl.functions.contacts import GetContactsRequest
from telethon.tl.types import InputPeerEmpty, InputPeerChannel, InputPeerUser
from telethon.errors import ChatAdminRequiredError, ChannelPrivateError, FloodWaitError, UserPrivacyRestrictedError

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration file
CONFIG_FILE = 'config.json'
DEFAULT_CONFIG = {
    'groups': [],
    'target': None,
    'delay': 300,  # Default delay of 5 minutes
    'active': False,
    'cycle_count': 0,
    'admin_id': None  # Will be set on first run
}

# Get API credentials on startup
def get_credentials():
    print("=" * 50)
    print("\n🔑 Telegram API Configuration 🔑\n")
    print("=" * 50)
    
    # Get API ID and API Hash
    api_id = input("\nEnter your API ID: ")
    api_hash = input("Enter your API Hash: ")
    phone = input("Enter your phone number (with country code, e.g., +628xxx): ")
    
    return int(api_id), api_hash, phone

# Initialize credentials
API_ID, API_HASH, PHONE_NUMBER = get_credentials()
SESSION_NAME = 'userbot_session'

# Initialize client
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# Config management functions
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

config = load_config()

# Helper function to check if user is admin
async def is_admin(user_id):
    # If admin_id is not set, set it to the first user who interacts with the bot
    if config['admin_id'] is None:
        config['admin_id'] = user_id
        save_config(config)
        await client.send_message(user_id, f"🔐 Anda telah ditetapkan sebagai admin bot dengan ID: {user_id}")
        return True
    return user_id == config['admin_id']

# Command handling
@client.on(events.NewMessage(pattern=r'\.join (.+)'))
async def join_group(event):
    # Check if the user is admin
    if not await is_admin(event.sender_id):
        return
        
    if not event.is_private:
        return
    
    group_name = event.pattern_match.group(1)
    try:
        await client(JoinChannelRequest(group_name))
        await event.respond(f"✅ Successfully joined {group_name}")
    except (ValueError, ChannelPrivateError, ChatAdminRequiredError) as e:
        await event.respond(f"❌ Failed to join {group_name}: {str(e)}")

@client.on(events.NewMessage(pattern=r'\.out (.+)'))
async def leave_group(event):
    # Check if the user is admin
    if not await is_admin(event.sender_id):
        return
        
    if not event.is_private:
        return
    
    group_name = event.pattern_match.group(1)
    try:
        await client(LeaveChannelRequest(group_name))
        await event.respond(f"✅ Successfully left {group_name}")
    except Exception as e:
        await event.respond(f"❌ Failed to leave {group_name}: {str(e)}")

@client.on(events.NewMessage(pattern=r'\.addgroup (.+)'))
async def add_group(event):
    # Check if the user is admin
    if not await is_admin(event.sender_id):
        return
        
    if not event.is_private:
        return
    
    group_name = event.pattern_match.group(1)
    try:
        entity = await client.get_entity(group_name)
        group_id = entity.id
        title = entity.title if hasattr(entity, 'title') else group_name
        
        # Check if group already exists in the list
        if not any(g['id'] == group_id for g in config['groups']):
            config['groups'].append({
                'id': group_id,
                'name': title,
                'username': group_name
            })
            save_config(config)
            await event.respond(f"✅ Added {title} to the group list")
        else:
            await event.respond(f"ℹ️ {title} is already in the group list")
    except Exception as e:
        await event.respond(f"❌ Failed to add group: {str(e)}")

@client.on(events.NewMessage(pattern=r'\.listgroups'))
async def list_groups(event):
    # Check if the user is admin
    if not await is_admin(event.sender_id):
        return
        
    if not event.is_private:
        return
    
    if not config['groups']:
        await event.respond("⚠️ No groups in the list")
        return
    
    groups_text = "📋 **List of Groups:**\n\n"
    for i, group in enumerate(config['groups'], 1):
        groups_text += f"{i}. {group['name']} (`{group['username']}`)\n"
    
    await event.respond(groups_text)

@client.on(events.NewMessage(pattern=r'\.delgroup (.+)'))
async def delete_group(event):
    # Check if the user is admin
    if not await is_admin(event.sender_id):
        return
        
    if not event.is_private:
        return
    
    group_name = event.pattern_match.group(1)
    try:
        # Try to find the group by username or ID
        found = False
        for i, group in enumerate(config['groups']):
            if group['username'] == group_name or str(group['id']) == group_name:
                del config['groups'][i]
                found = True
                save_config(config)
                await event.respond(f"✅ Removed {group['name']} from the group list")
                break
        
        if not found:
            await event.respond(f"❌ Group {group_name} not found in the list")
    except Exception as e:
        await event.respond(f"❌ Failed to remove group: {str(e)}")

@client.on(events.NewMessage(pattern=r'\.setdelay (\d+)'))
async def set_delay(event):
    # Check if the user is admin
    if not await is_admin(event.sender_id):
        return
        
    if not event.is_private:
        return
    
    delay = int(event.pattern_match.group(1))
    if delay < 30:
        await event.respond("⚠️ Delay must be at least 30 seconds")
        return
    
    config['delay'] = delay
    save_config(config)
    await event.respond(f"⏱️ Delay set to {delay} seconds")

@client.on(events.NewMessage(pattern=r'\.settarget (.+)'))
async def set_target(event):
    # Check if the user is admin
    if not await is_admin(event.sender_id):
        return
        
    if not event.is_private:
        return
    
    target_name = event.pattern_match.group(1)
    try:
        entity = await client.get_entity(target_name)
        config['target'] = {
            'id': entity.id,
            'name': entity.title if hasattr(entity, 'title') else target_name,
            'username': target_name
        }
        save_config(config)
        await event.respond(f"🎯 Target set to {config['target']['name']}")
    except Exception as e:
        await event.respond(f"❌ Failed to set target: {str(e)}")

@client.on(events.NewMessage(pattern=r'\.setadmin (.+)'))
async def set_admin(event):
    # Check if the user is admin
    if not await is_admin(event.sender_id):
        return
        
    if not event.is_private:
        return
    
    try:
        # Get the new admin ID
        new_admin_id = int(event.pattern_match.group(1).strip())
        
        # Update the admin ID
        old_admin_id = config['admin_id']
        config['admin_id'] = new_admin_id
        save_config(config)
        
        # Notify both old and new admin
        await event.respond(f"🔄 Admin ID telah diubah dari {old_admin_id} ke {new_admin_id}")
        
        # If the new admin is different from the current user, notify them
        if new_admin_id != event.sender_id:
            try:
                await client.send_message(new_admin_id, f"🔐 Anda telah ditetapkan sebagai admin baru untuk userbot oleh admin sebelumnya (ID: {old_admin_id})")
            except Exception as e:
                await event.respond(f"⚠️ Tidak dapat mengirim pesan ke admin baru: {str(e)}")
        
    except ValueError:
        await event.respond("❌ ID admin harus berupa angka")
    except Exception as e:
        await event.respond(f"❌ Gagal mengatur admin baru: {str(e)}")

@client.on(events.NewMessage(pattern=r'\.resetadmin'))
async def reset_admin(event):
    # Check if the user is admin
    if not await is_admin(event.sender_id):
        return
        
    if not event.is_private:
        return
    
    # Reset admin ID
    old_admin_id = config['admin_id']
    config['admin_id'] = None
    save_config(config)
    
    await event.respond(f"🔄 Admin ID telah direset. User pertama yang mengirim perintah akan menjadi admin baru.")

@client.on(events.NewMessage(pattern=r'\.getadmin'))
async def get_admin(event):
    # This command can be used by anyone to check who is the admin
    # Useful for users to know who to contact for access
    if not event.is_private:
        return
    
    if config['admin_id'] is None:
        await event.respond("🔑 Bot belum memiliki admin. User pertama yang mengirim perintah akan menjadi admin.")
    else:
        await event.respond(f"🔑 Admin ID saat ini: {config['admin_id']}")

@client.on(events.NewMessage(pattern=r'\.start'))
async def start_bot(event):
    # Check if the user is admin
    if not await is_admin(event.sender_id):
        return
        
    if not event.is_private:
        return
    
    if not config['groups']:
        await event.respond("⚠️ You need to add groups first using .addgroup command")
        return
    
    if not config['target']:
        await event.respond("⚠️ You need to set a target first using .settarget command")
        return
    
    config['active'] = True
    config['cycle_count'] = 0
    save_config(config)
    await event.respond("▶️ Bot started successfully")
    
    # Start the message copying process
    asyncio.create_task(copy_messages(event.chat_id))

@client.on(events.NewMessage(pattern=r'\.stop'))
async def stop_bot(event):
    # Check if the user is admin
    if not await is_admin(event.sender_id):
        return
        
    if not event.is_private:
        return
    
    config['active'] = False
    save_config(config)
    await event.respond("⏹️ Bot stopped successfully")

@client.on(events.NewMessage(pattern=r'\.status'))
async def bot_status(event):
    # Check if the user is admin
    if not await is_admin(event.sender_id):
        return
        
    if not event.is_private:
        return
    
    status = "🟢 Active" if config['active'] else "🔴 Inactive"
    groups_count = len(config['groups'])
    target_info = f"{config['target']['name']}" if config['target'] else "Not set"
    delay = config['delay']
    cycles = config['cycle_count']
    admin_id = config['admin_id']
    
    status_text = f"📊 **Bot Status:**\n\n"
    status_text += f"Status: {status}\n"
    status_text += f"Source Groups: {groups_count}\n"
    status_text += f"Target Group: {target_info}\n"
    status_text += f"Delay: {delay} seconds\n"
    status_text += f"Completed Cycles: {cycles}\n"
    status_text += f"Admin ID: {admin_id}\n"
    
    await event.respond(status_text)

@client.on(events.NewMessage(pattern=r'\.help'))
async def help_command(event):
    # Check if the user is admin
    if not await is_admin(event.sender_id):
        return
        
    if not event.is_private:
        return
    
    help_text = """
📚 **Userbot Commands**

**Group Management:**
`.join <username>` - Join a group
`.out <username>` - Leave a group
`.addgroup <username>` - Add a group to source list
`.delgroup <username>` - Remove a group from source list
`.listgroups` - List all source groups

**Configuration:**
`.setdelay <seconds>` - Set delay between copies
`.settarget <username>` - Set target group
`.setadmin <user_id>` - Set new admin by ID
`.resetadmin` - Reset admin (next user becomes admin)
`.getadmin` - Check current admin ID (anyone can use)

**Operations:**
`.start` - Start the bot
`.stop` - Stop the bot
`.status` - Check bot status
`.help` - Show this help message

**Invite Feature:**
`.invite <group_link>` - Invite mutual contacts to a group

**OTP Feature:**
`.getotp` - Get latest OTP from Telegram official (+42777)

**Note:** Only the admin/owner can use these commands except .getadmin.
"""
    await event.respond(help_text)

# Add Invite Contacts feature
@client.on(events.NewMessage(pattern=r'\.invite (.+)'))
async def invite_contacts(event):
    # Check if the user is admin
    if not await is_admin(event.sender_id):
        return
        
    if not event.is_private:
        return
    
    target_group = event.pattern_match.group(1).strip()
    
    try:
        # Status update message
        status_msg = await event.respond("⏳ Processing invitation request...")
        
        # Try to get group entity, join if not already joined
        try:
            if target_group.startswith('https://t.me/+') or target_group.startswith('https://t.me/joinchat/'):
                # Extract hash from invite link
                invite_hash = target_group.split('/')[-1]
                if invite_hash.startswith('+'):
                    invite_hash = invite_hash[1:]
                
                # Try to join using the invite link
                try:
                    await client(ImportChatInviteRequest(invite_hash))
                    await status_msg.edit("✅ Joined the group via invite link. Now getting group info...")
                except Exception as e:
                    if "ALREADY_PARTICIPANT" not in str(e):
                        await status_msg.edit(f"⚠️ Error joining group: {str(e)}")
                        return
                    else:
                        await status_msg.edit("ℹ️ Already a member of this group. Proceeding...")
                
                # Get dialogs to find the recently joined group
                dialogs = await client(GetDialogsRequest(
                    offset_date=None,
                    offset_id=0,
                    offset_peer=InputPeerEmpty(),
                    limit=50,
                    hash=0
                ))
                
                target_entity = None
                for dialog in dialogs.dialogs:
                    if dialog.peer:
                        try:
                            dialog_entity = await client.get_entity(dialog.peer)
                            # Try to find the recently joined group
                            if hasattr(dialog_entity, 'title'):
                                target_entity = dialog_entity
                                break
                        except Exception:
                            continue
                
                if not target_entity:
                    await status_msg.edit("❌ Could not find the target group after joining")
                    return
            else:
                # Regular username
                try:
                    target_entity = await client.get_entity(target_group)
                    try:
                        await client(JoinChannelRequest(target_group))
                        await status_msg.edit(f"✅ Joined the group {target_entity.title}. Preparing to invite contacts...")
                    except Exception as e:
                        if "ALREADY_PARTICIPANT" not in str(e):
                            await status_msg.edit(f"⚠️ Error joining group: {str(e)}")
                            return
                        else:
                            await status_msg.edit(f"ℹ️ Already a member of {target_entity.title}. Proceeding to invite contacts...")
                except Exception as e:
                    await status_msg.edit(f"❌ Error getting group info: {str(e)}")
                    return
        
        # Get all contacts
        contacts = await client(GetContactsRequest(hash=0))
        if not contacts.contacts:
            await status_msg.edit("⚠️ No contacts found in your Telegram account")
            return
        
        await status_msg.edit(f"🔄 Found {len(contacts.contacts)} contacts. Checking for mutual contacts...")
        
        # Get mutual contacts (those who have you in their contacts)
        mutual_contacts = []
        for contact in contacts.contacts:
            try:
                user = await client.get_entity(contact.user_id)
                is_mutual = user.mutual_contact
                if is_mutual:
                    mutual_contacts.append(InputPeerUser(user.id, user.access_hash))
            except Exception as e:
                logger.error(f"Error checking contact {contact.user_id}: {e}")
        
        if not mutual_contacts:
            await status_msg.edit("⚠️ No mutual contacts found")
            return
        
        await status_msg.edit(f"🔄 Found {len(mutual_contacts)} mutual contacts. Starting invitation process...")
        
        # Invite mutual contacts in smaller batches to avoid flood limits
        batch_size = 5  # Invite 5 contacts at a time
        success_count = 0
        failed_count = 0
        
        for i in range(0, len(mutual_contacts), batch_size):
            batch = mutual_contacts[i:i+batch_size]
            try:
                # Create an InputPeerChannel from the target entity
                input_channel = InputPeerChannel(target_entity.id, target_entity.access_hash)
                
                # Invite the batch of contacts
                await client(InviteToChannelRequest(
                    channel=input_channel,
                    users=batch
                ))
                success_count += len(batch)
                
                # Update status message
                await status_msg.edit(f"🔄 Invited {success_count}/{len(mutual_contacts)} contacts... ({failed_count} failed)")
                
                # Sleep to avoid hitting rate limits
                await asyncio.sleep(2)
                
            except UserPrivacyRestrictedError:
                failed_count += len(batch)
                await status_msg.edit(f"🔄 Some users' privacy settings prevented invitation. Invited {success_count}/{len(mutual_contacts)} contacts... ({failed_count} failed)")
            except FloodWaitError as e:
                await status_msg.edit(f"⚠️ Hit rate limit. Waiting for {e.seconds} seconds...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                failed_count += len(batch)
                await status_msg.edit(f"⚠️ Error inviting batch: {str(e)}")
                await asyncio.sleep(2)
        
        # Final status update
        await status_msg.edit(f"✅ Invitation process completed!\n\n"
                             f"• Target Group: {target_entity.title}\n"
                             f"• Total Contacts: {len(contacts.contacts)}\n"
                             f"• Mutual Contacts: {len(mutual_contacts)}\n"
                             f"• Successfully Invited: {success_count}\n"
                             f"• Failed to Invite: {failed_count}")
    
    except Exception as e:
        await event.respond(f"❌ Error during invitation process: {str(e)}")

# Add Get OTP feature from +42777
@client.on(events.NewMessage(pattern=r'\.getotp'))
async def get_otp(event):
    # Check if the user is admin
    if not await is_admin(event.sender_id):
        return
        
    if not event.is_private:
        return
    
    try:
        # Status update message
        status_msg = await event.respond("🔍 Searching for OTP messages from Telegram (+42777)...")
        
        # Get the Telegram service notifications chat (42777)
        try:
            telegram_service = await client.get_entity(42777)
        except Exception:
            # Fallback to 777000 if 42777 not found
            try:
                telegram_service = await client.get_entity(777000)
                await status_msg.edit("ℹ️ Using Telegram service notifications (777000) instead of +42777...")
            except Exception as e:
                await status_msg.edit(f"❌ Failed to find Telegram notification services: {str(e)}")
                return
        
        # Get recent messages (increase limit to ensure we find OTP messages)
        messages = await client.get_messages(telegram_service, limit=30)
        
        # Filter messages likely containing OTP
        otp_messages = []
        otp_keywords = ["code", "código", "kod", "verification", "verificación", "password", "otp", "one-time", "login"]
        
        for msg in messages:
            if msg.message:
                message_text = msg.message.lower()
                # Check if this looks like an OTP message
                if any(keyword in message_text for keyword in otp_keywords) or any(seg.isdigit() and 4 <= len(seg) <= 6 for seg in message_text.split()):
                    otp_messages.append(msg)
        
        if not otp_messages:
            await status_msg.edit("❌ No recent OTP messages found from Telegram")
            return
        
        # Sort by date (newest first)
        otp_messages.sort(key=lambda x: x.date, reverse=True)
        
        # Display the OTP messages
        result = "🔐 **Recent OTP Messages:**\n\n"
        
        for i, msg in enumerate(otp_messages[:5], 1):  # Show max 5 most recent OTP messages
            # Format the date
            date_str = msg.date.strftime("%Y-%m-%d %H:%M:%S")
            
            # Add message to result
            result += f"**{i}. {date_str}**\n"
            result += f"{msg.message}\n\n"
        
        await status_msg.edit(result)
    
    except Exception as e:
        await event.respond(f"❌ Error retrieving OTP messages: {str(e)}")

# Main functionality to copy messages
async def copy_messages(owner_id):
    while config['active']:
        try:
            if not config['groups'] or not config['target']:
                await client.send_message(owner_id, "⚠️ Missing configuration, stopping bot")
                config['active'] = False
                save_config(config)
                break
            
            # Select random source group
            source_group = random.choice(config['groups'])
            
            # Get last 30 messages from the source group (increased from 20 to find more media)
            messages = await client(GetHistoryRequest(
                peer=source_group['id'],
                limit=30,
                offset_date=None,
                offset_id=0,
                max_id=0,
                min_id=0,
                add_offset=0,
                hash=0
            ))
            
            if not messages.messages:
                await client.send_message(owner_id, f"⚠️ No messages found in {source_group['name']}")
                continue
            
            # Filter messages with media and caption first
            media_with_caption = [msg for msg in messages.messages 
                               if msg.media and hasattr(msg, 'message') and msg.message]
            
            # If there are messages with media and caption, prioritize them
            if media_with_caption:
                message = random.choice(media_with_caption)
                message_type = "Media with caption"
            else:
                # Otherwise, just pick any message with media
                media_messages = [msg for msg in messages.messages if msg.media]
                if media_messages:
                    message = random.choice(media_messages)
                    message_type = "Media only"
                else:
                    # If no media found, pick any random message
                    message = random.choice(messages.messages)
                    message_type = "Text only"
            
            # Copy to target
            target_group = config['target']['id']
            sent_message = await client.send_message(target_group, message)
            
            if sent_message:
                config['cycle_count'] += 1
                save_config(config)
                
                # Format the timestamp
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # Prepare info about the original message
                message_info = ""
                if hasattr(message, 'message') and message.message:
                    # Truncate message preview if too long
                    preview = message.message[:50] + "..." if len(message.message) > 50 else message.message
                    message_info = f"Content: \"{preview}\"\n"
                
                # Send status update to owner using quote formatting
                status_message = (
                    f"✅ **Cycle #{config['cycle_count']} completed at {timestamp}**\n\n"
                    f"Source: {source_group['name']}\n"
                    f"Target: {config['target']['name']}\n"
                    f"Type: {message_type}\n"
                    f"{message_info}"
                    f"Next copy in {config['delay']} seconds"
                )
                await client.send_message(owner_id, status_message)
            
            # Wait for the specified delay
            await asyncio.sleep(config['delay'])
            
        except FloodWaitError as e:
            # Handle Telegram rate limits
            wait_time = e.seconds
            await client.send_message(
                owner_id, 
                f"⚠️ Hit rate limit, waiting for {wait_time} seconds"
            )
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error(f"Error during message copying: {e}")
            await client.send_message(
                owner_id, 
                f"❌ Error during copy: {str(e)}\nRetrying in {config['delay']} seconds"
            )
            await asyncio.sleep(config['delay'])

# Main function
async def main():
    print("\n" + "=" * 50)
    print("\n📱 Starting Telegram Userbot 📱\n")
    print("=" * 50 + "\n")
    
    await client.start(phone=PHONE_NUMBER)
    me = await client.get_me()
    logger.info(f"Userbot started as @{me.username}")
    print(f"\n✅ Logged in as: @{me.username}")
    print(f"📞 Phone: {me.phone}")
    print(f"🆔 User ID: {me.id}")
    print("\n" + "-" * 50)
    print("\nUserbot is running! Send commands to your account in Telegram.")
    print("Type .help in private chat to see available commands.")
    print("-" * 50 + "\n")
    
    # If the bot was active before restart, resume it
    if config['active'] and config['admin_id']:
        await client.send_message(config['admin_id'], "🔄 Bot restarted and continuing operation")
        asyncio.create_task(copy_messages(config['admin_id']))
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n⏹️ Userbot has been stopped manually.")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nExiting...")
