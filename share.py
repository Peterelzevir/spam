#!/usr/bin/env python3
# Telegram Userbot for Content Forwarding
# This script allows you to forward content from source groups to target groups
# using Telethon library

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import InputChannel, MessageMediaPhoto, MessageMediaDocument
from telethon.errors import SessionPasswordNeededError

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration file
CONFIG_FILE = 'userbot_config.json'

# Default configuration
DEFAULT_CONFIG = {
    'accounts': {},
    'sources': [],
    'targets': [],
    'delay': 60,  # Default delay in seconds
    'active': False,
    'media_types': ['photo', 'video', 'document', 'audio'],
    'caption_only': False,
}

# Initialize or load configuration
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_CONFIG

# Save configuration
def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# Global variables
config = load_config()
clients = {}  # Store active client sessions

# Terminal UI colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Clear terminal screen
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# Print header
def print_header():
    clear_screen()
    print(f"{Colors.HEADER}{Colors.BOLD}==================================={Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}     TELEGRAM USERBOT MANAGER     {Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}==================================={Colors.ENDC}")
    print()

# Print menu
def print_menu():
    print(f"{Colors.BLUE}1. {Colors.ENDC}Add Userbot Account")
    print(f"{Colors.BLUE}2. {Colors.ENDC}Delete Userbot Account")
    print(f"{Colors.BLUE}3. {Colors.ENDC}List Userbot Accounts")
    print(f"{Colors.BLUE}4. {Colors.ENDC}Add Source Group")
    print(f"{Colors.BLUE}5. {Colors.ENDC}Delete Source Group")
    print(f"{Colors.BLUE}6. {Colors.ENDC}Add Target Group")
    print(f"{Colors.BLUE}7. {Colors.ENDC}Delete Target Group")
    print(f"{Colors.BLUE}8. {Colors.ENDC}List Groups (Sources & Targets)")
    print(f"{Colors.BLUE}9. {Colors.ENDC}Set Forwarding Delay")
    print(f"{Colors.BLUE}10.{Colors.ENDC} Configure Media Types")
    print(f"{Colors.BLUE}11.{Colors.ENDC} " + ("Stop Forwarding" if config['active'] else "Start Forwarding"))
    print(f"{Colors.BLUE}12.{Colors.ENDC} Show Userbot Status")
    print(f"{Colors.BLUE}0. {Colors.ENDC}Exit")
    print()

# Add a new userbot account
async def add_account():
    print_header()
    print(f"{Colors.BOLD}ADD NEW USERBOT ACCOUNT{Colors.ENDC}")
    print("Please provide the following information:")
    
    name = input("Account Name: ")
    if name in config['accounts']:
        print(f"{Colors.FAIL}Account with this name already exists!{Colors.ENDC}")
        input("Press Enter to continue...")
        return
    
    api_id = input("API ID: ")
    api_hash = input("API Hash: ")
    phone = input("Phone Number (with country code): ")
    
    # Create new client
    client = TelegramClient(f"sessions/{name}", api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        await client.send_code_request(phone)
        code = input("Enter the code you received: ")
        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            password = input("Two-step verification enabled. Please enter your password: ")
            await client.sign_in(password=password)
    
    me = await client.get_me()
    await client.disconnect()
    
    # Save to config
    config['accounts'][name] = {
        'api_id': api_id,
        'api_hash': api_hash,
        'phone': phone,
        'username': me.username if me.username else "",
        'first_name': me.first_name if me.first_name else "",
        'last_name': me.last_name if me.last_name else "",
    }
    save_config(config)
    
    print(f"{Colors.GREEN}Account {name} added successfully!{Colors.ENDC}")
    input("Press Enter to continue...")

# Delete a userbot account
def delete_account():
    print_header()
    print(f"{Colors.BOLD}DELETE USERBOT ACCOUNT{Colors.ENDC}")
    
    if not config['accounts']:
        print(f"{Colors.WARNING}No accounts found!{Colors.ENDC}")
        input("Press Enter to continue...")
        return
    
    print("Available accounts:")
    for idx, name in enumerate(config['accounts'].keys(), 1):
        print(f"{idx}. {name}")
    
    try:
        choice = int(input("\nSelect account number to delete (0 to cancel): "))
        if choice == 0:
            return
        
        if 1 <= choice <= len(config['accounts']):
            name = list(config['accounts'].keys())[choice - 1]
            confirm = input(f"Are you sure you want to delete {name}? (y/n): ")
            
            if confirm.lower() == 'y':
                # Remove session file if exists
                session_file = f"sessions/{name}.session"
                if os.path.exists(session_file):
                    os.remove(session_file)
                
                # Remove from config
                del config['accounts'][name]
                save_config(config)
                print(f"{Colors.GREEN}Account {name} deleted successfully!{Colors.ENDC}")
            else:
                print("Deletion cancelled.")
        else:
            print(f"{Colors.FAIL}Invalid selection!{Colors.ENDC}")
    except ValueError:
        print(f"{Colors.FAIL}Please enter a valid number!{Colors.ENDC}")
    
    input("Press Enter to continue...")

# List all userbot accounts
def list_accounts():
    print_header()
    print(f"{Colors.BOLD}USERBOT ACCOUNTS{Colors.ENDC}")
    
    if not config['accounts']:
        print(f"{Colors.WARNING}No accounts found!{Colors.ENDC}")
    else:
        print(f"{'Name':<15} {'Username':<15} {'Phone':<15} {'Status':<10}")
        print("-" * 55)
        for name, acc in config['accounts'].items():
            username = acc.get('username', 'N/A')
            phone = acc.get('phone', 'N/A')
            status = "Active" if name in clients else "Inactive"
            print(f"{name:<15} {username:<15} {phone:<15} {status:<10}")
    
    input("\nPress Enter to continue...")

# Add a source group
async def add_source():
    print_header()
    print(f"{Colors.BOLD}ADD SOURCE GROUP{Colors.ENDC}")
    
    if not config['accounts']:
        print(f"{Colors.FAIL}No accounts found! Please add an account first.{Colors.ENDC}")
        input("Press Enter to continue...")
        return
    
    # Select account
    print("Select account to use:")
    for idx, name in enumerate(config['accounts'].keys(), 1):
        print(f"{idx}. {name}")
    
    try:
        choice = int(input("\nSelect account number (0 to cancel): "))
        if choice == 0:
            return
        
        if 1 <= choice <= len(config['accounts']):
            account_name = list(config['accounts'].keys())[choice - 1]
            account = config['accounts'][account_name]
            
            # Connect to client
            client = TelegramClient(f"sessions/{account_name}", account['api_id'], account['api_hash'])
            await client.connect()
            
            if not await client.is_user_authorized():
                print(f"{Colors.FAIL}Account not authorized! Please delete and add it again.{Colors.ENDC}")
                await client.disconnect()
                input("Press Enter to continue...")
                return
            
            # Get groups/channels
            dialogs = await client.get_dialogs()
            groups = [(i, d) for i, d in enumerate(dialogs, 1) if d.is_group or d.is_channel]
            
            print("\nAvailable Groups/Channels:")
            for idx, dialog in groups:
                entity_type = "Group" if dialog.is_group else "Channel"
                print(f"{idx}. {dialog.name} ({entity_type})")
            
            group_choice = int(input("\nSelect group/channel number (0 to cancel): "))
            if group_choice == 0:
                await client.disconnect()
                return
            
            if 1 <= group_choice <= len(groups):
                selected_idx, selected_dialog = groups[group_choice - 1]
                
                # Check if already exists
                for source in config['sources']:
                    if source['id'] == selected_dialog.id:
                        print(f"{Colors.FAIL}This group/channel is already a source!{Colors.ENDC}")
                        await client.disconnect()
                        input("Press Enter to continue...")
                        return
                
                # Add to sources
                config['sources'].append({
                    'id': selected_dialog.id,
                    'name': selected_dialog.name,
                    'type': 'group' if selected_dialog.is_group else 'channel',
                    'account': account_name
                })
                save_config(config)
                print(f"{Colors.GREEN}Source {selected_dialog.name} added successfully!{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}Invalid selection!{Colors.ENDC}")
            
            await client.disconnect()
        else:
            print(f"{Colors.FAIL}Invalid selection!{Colors.ENDC}")
    except ValueError:
        print(f"{Colors.FAIL}Please enter a valid number!{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}Error: {str(e)}{Colors.ENDC}")
    
    input("Press Enter to continue...")

# Delete a source group
def delete_source():
    print_header()
    print(f"{Colors.BOLD}DELETE SOURCE GROUP{Colors.ENDC}")
    
    if not config['sources']:
        print(f"{Colors.WARNING}No source groups found!{Colors.ENDC}")
        input("Press Enter to continue...")
        return
    
    print("Available source groups:")
    for idx, source in enumerate(config['sources'], 1):
        print(f"{idx}. {source['name']} (Account: {source['account']})")
    
    try:
        choice = int(input("\nSelect source number to delete (0 to cancel): "))
        if choice == 0:
            return
        
        if 1 <= choice <= len(config['sources']):
            source = config['sources'][choice - 1]
            confirm = input(f"Are you sure you want to delete '{source['name']}' from sources? (y/n): ")
            
            if confirm.lower() == 'y':
                del config['sources'][choice - 1]
                save_config(config)
                print(f"{Colors.GREEN}Source deleted successfully!{Colors.ENDC}")
            else:
                print("Deletion cancelled.")
        else:
            print(f"{Colors.FAIL}Invalid selection!{Colors.ENDC}")
    except ValueError:
        print(f"{Colors.FAIL}Please enter a valid number!{Colors.ENDC}")
    
    input("Press Enter to continue...")

# Add a target group
async def add_target():
    print_header()
    print(f"{Colors.BOLD}ADD TARGET GROUP{Colors.ENDC}")
    
    if not config['accounts']:
        print(f"{Colors.FAIL}No accounts found! Please add an account first.{Colors.ENDC}")
        input("Press Enter to continue...")
        return
    
    # Select account
    print("Select account to use:")
    for idx, name in enumerate(config['accounts'].keys(), 1):
        print(f"{idx}. {name}")
    
    try:
        choice = int(input("\nSelect account number (0 to cancel): "))
        if choice == 0:
            return
        
        if 1 <= choice <= len(config['accounts']):
            account_name = list(config['accounts'].keys())[choice - 1]
            account = config['accounts'][account_name]
            
            # Connect to client
            client = TelegramClient(f"sessions/{account_name}", account['api_id'], account['api_hash'])
            await client.connect()
            
            if not await client.is_user_authorized():
                print(f"{Colors.FAIL}Account not authorized! Please delete and add it again.{Colors.ENDC}")
                await client.disconnect()
                input("Press Enter to continue...")
                return
            
            # Get groups/channels
            dialogs = await client.get_dialogs()
            groups = [(i, d) for i, d in enumerate(dialogs, 1) if d.is_group or d.is_channel]
            
            print("\nAvailable Groups/Channels:")
            for idx, dialog in groups:
                entity_type = "Group" if dialog.is_group else "Channel"
                print(f"{idx}. {dialog.name} ({entity_type})")
            
            group_choice = int(input("\nSelect group/channel number (0 to cancel): "))
            if group_choice == 0:
                await client.disconnect()
                return
            
            if 1 <= group_choice <= len(groups):
                selected_idx, selected_dialog = groups[group_choice - 1]
                
                # Check if already exists
                for target in config['targets']:
                    if target['id'] == selected_dialog.id:
                        print(f"{Colors.FAIL}This group/channel is already a target!{Colors.ENDC}")
                        await client.disconnect()
                        input("Press Enter to continue...")
                        return
                
                # Add to targets
                config['targets'].append({
                    'id': selected_dialog.id,
                    'name': selected_dialog.name,
                    'type': 'group' if selected_dialog.is_group else 'channel',
                    'account': account_name
                })
                save_config(config)
                print(f"{Colors.GREEN}Target {selected_dialog.name} added successfully!{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}Invalid selection!{Colors.ENDC}")
            
            await client.disconnect()
        else:
            print(f"{Colors.FAIL}Invalid selection!{Colors.ENDC}")
    except ValueError:
        print(f"{Colors.FAIL}Please enter a valid number!{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}Error: {str(e)}{Colors.ENDC}")
    
    input("Press Enter to continue...")

# Delete a target group
def delete_target():
    print_header()
    print(f"{Colors.BOLD}DELETE TARGET GROUP{Colors.ENDC}")
    
    if not config['targets']:
        print(f"{Colors.WARNING}No target groups found!{Colors.ENDC}")
        input("Press Enter to continue...")
        return
    
    print("Available target groups:")
    for idx, target in enumerate(config['targets'], 1):
        print(f"{idx}. {target['name']} (Account: {target['account']})")
    
    try:
        choice = int(input("\nSelect target number to delete (0 to cancel): "))
        if choice == 0:
            return
        
        if 1 <= choice <= len(config['targets']):
            target = config['targets'][choice - 1]
            confirm = input(f"Are you sure you want to delete '{target['name']}' from targets? (y/n): ")
            
            if confirm.lower() == 'y':
                del config['targets'][choice - 1]
                save_config(config)
                print(f"{Colors.GREEN}Target deleted successfully!{Colors.ENDC}")
            else:
                print("Deletion cancelled.")
        else:
            print(f"{Colors.FAIL}Invalid selection!{Colors.ENDC}")
    except ValueError:
        print(f"{Colors.FAIL}Please enter a valid number!{Colors.ENDC}")
    
    input("Press Enter to continue...")

# List all groups (sources and targets)
def list_groups():
    print_header()
    print(f"{Colors.BOLD}GROUPS CONFIGURATION{Colors.ENDC}")
    
    print(f"{Colors.BOLD}SOURCE GROUPS:{Colors.ENDC}")
    if not config['sources']:
        print("No source groups configured.")
    else:
        for idx, source in enumerate(config['sources'], 1):
            print(f"{idx}. {source['name']} (Account: {source['account']})")
    
    print(f"\n{Colors.BOLD}TARGET GROUPS:{Colors.ENDC}")
    if not config['targets']:
        print("No target groups configured.")
    else:
        for idx, target in enumerate(config['targets'], 1):
            print(f"{idx}. {target['name']} (Account: {target['account']})")
    
    input("\nPress Enter to continue...")

# Set forwarding delay
def set_delay():
    print_header()
    print(f"{Colors.BOLD}SET FORWARDING DELAY{Colors.ENDC}")
    print(f"Current delay: {config['delay']} seconds")
    
    try:
        new_delay = float(input("\nEnter new delay in seconds (0 to cancel): "))
        if new_delay == 0:
            return
        
        if new_delay < 0:
            print(f"{Colors.FAIL}Delay cannot be negative!{Colors.ENDC}")
        else:
            config['delay'] = new_delay
            save_config(config)
            print(f"{Colors.GREEN}Delay updated to {new_delay} seconds!{Colors.ENDC}")
    except ValueError:
        print(f"{Colors.FAIL}Please enter a valid number!{Colors.ENDC}")
    
    input("Press Enter to continue...")

# Configure media types
def configure_media():
    print_header()
    print(f"{Colors.BOLD}CONFIGURE MEDIA TYPES{Colors.ENDC}")
    
    media_types = config.get('media_types', ['photo', 'video', 'document', 'audio'])
    caption_only = config.get('caption_only', False)
    
    print("Current configuration:")
    print(f"Photos: {'✓' if 'photo' in media_types else '✗'}")
    print(f"Videos: {'✓' if 'video' in media_types else '✗'}")
    print(f"Documents: {'✓' if 'document' in media_types else '✗'}")
    print(f"Audio: {'✓' if 'audio' in media_types else '✗'}")
    print(f"Caption only mode: {'✓' if caption_only else '✗'}")
    print(f"Video to link (v2l): {'✓' if config.get('v2l', False) else '✗'}")
    
    print("\nUpdate configuration:")
    print("1. Toggle Photos")
    print("2. Toggle Videos")
    print("3. Toggle Documents")
    print("4. Toggle Audio")
    print("5. Toggle Caption Only Mode")
    print("6. Toggle Video to Link (v2l)")
    print("0. Save and Return")
    
    choice = input("\nSelect option: ")
    
    if choice == '1':
        if 'photo' in media_types:
            media_types.remove('photo')
        else:
            media_types.append('photo')
    elif choice == '2':
        if 'video' in media_types:
            media_types.remove('video')
        else:
            media_types.append('video')
    elif choice == '3':
        if 'document' in media_types:
            media_types.remove('document')
        else:
            media_types.append('document')
    elif choice == '4':
        if 'audio' in media_types:
            media_types.remove('audio')
        else:
            media_types.append('audio')
    elif choice == '5':
        config['caption_only'] = not caption_only
    elif choice == '6':
        config['v2l'] = not config.get('v2l', False)
    
    config['media_types'] = media_types
    save_config(config)
    
    if choice != '0':
        configure_media()  # Show the menu again

# Show userbot status
def show_status():
    print_header()
    print(f"{Colors.BOLD}USERBOT STATUS{Colors.ENDC}")
    
    print(f"Status: {Colors.GREEN if config['active'] else Colors.FAIL}{'Active' if config['active'] else 'Inactive'}{Colors.ENDC}")
    print(f"Forwarding Delay: {config['delay']} seconds")
    print(f"Configured Media Types: {', '.join(config.get('media_types', ['photo', 'video', 'document', 'audio']))}")
    print(f"Caption Only Mode: {'Enabled' if config.get('caption_only', False) else 'Disabled'}")
    print(f"Video to Link (v2l): {'Enabled' if config.get('v2l', False) else 'Disabled'}")
    print(f"Accounts: {len(config['accounts'])}")
    print(f"Source Groups: {len(config['sources'])}")
    print(f"Target Groups: {len(config['targets'])}")
    
    if config['active']:
        print(f"\n{Colors.BOLD}Active Accounts:{Colors.ENDC}")
        for name in clients.keys():
            print(f"- {name}")
    
    input("\nPress Enter to continue...")

# Convert video to link (v2l functionality)
async def get_media_link(client, message):
    """Get a direct link for media if possible"""
    if not message.media:
        return None
    
    try:
        if hasattr(message.media, 'document') and message.media.document.mime_type.startswith('video/'):
            # Download to memory
            file_data = await client.download_media(message.media, bytes)
            
            # Here you would typically upload to a hosting service and get a link
            # This is a simplified placeholder - in a real implementation,
            # you would upload the file to a service of your choice
            
            # For demonstration purposes only:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"video_{timestamp}.mp4"
            
            # Save locally (for demonstration)
            if not os.path.exists("media"):
                os.makedirs("media")
            
            with open(f"media/{filename}", "wb") as f:
                f.write(file_data)
            
            # Placeholder link (in a real implementation, this would be a real URL)
            # Here you would integrate with a file hosting service API
            return f"https://example.com/media/{filename}"
    except Exception as e:
        logger.error(f"Error generating media link: {str(e)}")
    
    return None

# Handle new messages from source groups and forward to target groups
async def handle_new_message(event):
    # Skip if not active
    if not config['active']:
        return
    
    message = event.message
    
    # Check if the message has the desired media type
    has_media = False
    media_type = None
    
    if message.media:
        if isinstance(message.media, MessageMediaPhoto) and 'photo' in config['media_types']:
            has_media = True
            media_type = 'photo'
        elif hasattr(message.media, 'document'):
            # Check for video
            if message.media.document.mime_type and message.media.document.mime_type.startswith('video/') and 'video' in config['media_types']:
                has_media = True
                media_type = 'video'
            # Check for audio
            elif message.media.document.mime_type and message.media.document.mime_type.startswith('audio/') and 'audio' in config['media_types']:
                has_media = True
                media_type = 'audio'
            # Check for any other document
            elif 'document' in config['media_types']:
                has_media = True
                media_type = 'document'
    
    # Skip if no media or caption-only mode and no caption
    if config.get('caption_only', False) and not message.text and not message.caption:
        return
    
    if not has_media and not config.get('caption_only', False):
        return
    
    # Get source account
    source_account = next((s['account'] for s in config['sources'] if s['id'] == event.chat_id), None)
    if not source_account or source_account not in clients:
        return
    
    # Handle v2l (video to link)
    media_link = None
    if config.get('v2l', False) and media_type == 'video':
        media_link = await get_media_link(clients[source_account], message)
    
    # Forward to all target groups
    for target in config['targets']:
        target_account = target['account']
        
        if target_account in clients:
            try:
                # Get the target entity
                target_entity = await clients[target_account].get_entity(target['id'])
                
                if media_link:
                    # Send message with video link
                    caption = message.caption if message.caption else ""
                    caption = f"{caption}\n\n{media_link}" if caption else media_link
                    await clients[target_account].send_message(
                        target_entity,
                        caption
                    )
                elif has_media and not config.get('caption_only', False):
                    # Forward media with caption
                    await clients[target_account].send_file(
                        target_entity,
                        message.media,
                        caption=message.caption if message.caption else ""
                    )
                else:
                    # Caption-only mode
                    text_content = message.caption if message.caption else message.text
                    if text_content:
                        await clients[target_account].send_message(
                            target_entity,
                            text_content
                        )
                
                # Log the forwarding
                source_name = next((s['name'] for s in config['sources'] if s['id'] == event.chat_id), "Unknown")
                logger.info(f"Forwarded {media_type if media_type else 'message'} from {source_name} to {target['name']}")
                
                # Delay between forwards
                await asyncio.sleep(config['delay'])
            except Exception as e:
                logger.error(f"Error forwarding to {target['name']}: {str(e)}")
                continue

# Start or stop forwarding
async def toggle_forwarding():
    global clients
    
    print_header()
    print(f"{Colors.BOLD}{'STOP' if config['active'] else 'START'} FORWARDING{Colors.ENDC}")
    
    if config['active']:
        # Stop forwarding
        confirm = input("Are you sure you want to stop forwarding? (y/n): ")
        if confirm.lower() == 'y':
            config['active'] = False
            save_config(config)
            
            # Disconnect all clients
            for client in clients.values():
                await client.disconnect()
            clients = {}
            
            print(f"{Colors.GREEN}Forwarding stopped successfully!{Colors.ENDC}")
        else:
            print("Operation cancelled.")
    else:
        # Check if sources and targets are configured
        if not config['sources']:
            print(f"{Colors.FAIL}No source groups configured! Please add at least one source.{Colors.ENDC}")
            input("Press Enter to continue...")
            return
        
        if not config['targets']:
            print(f"{Colors.FAIL}No target groups configured! Please add at least one target.{Colors.ENDC}")
            input("Press Enter to continue...")
            return
        
        # Start forwarding
        try:
            # Connect all required accounts
            unique_accounts = set([s['account'] for s in config['sources']] + [t['account'] for t in config['targets']])
            
            for account_name in unique_accounts:
                if account_name not in config['accounts']:
                    print(f"{Colors.FAIL}Account {account_name} not found in configuration!{Colors.ENDC}")
                    input("Press Enter to continue...")
                    return
                
                account = config['accounts'][account_name]
                client = TelegramClient(f"sessions/{account_name}", account['api_id'], account['api_hash'])
                await client.connect()
                
                if not await client.is_user_authorized():
                    print(f"{Colors.FAIL}Account {account_name} not authorized! Please delete and add it again.{Colors.ENDC}")
                    await client.disconnect()
                    input("Press Enter to continue...")
                    return
                
                clients[account_name] = client
            
            # Set up event handlers for each source
            for source in config['sources']:
                source_account = source['account']
                source_id = source['id']
                
                # Add event handler
                clients[source_account].add_event_handler(
                    handle_new_message,
                    events.NewMessage(chats=source_id)
                )
            
            config['active'] = True
            save_config(config)
            print(f"{Colors.GREEN}Forwarding started successfully!{Colors.ENDC}")
            print(f"Listening for new messages from {len(config['sources'])} sources.")
            print(f"Messages will be forwarded to {len(config['targets'])} targets with a {config['delay']} second delay.")
            print("\nPress Enter to return to the menu (forwarding continues in background).")
        except Exception as e:
            print(f"{Colors.FAIL}Error starting forwarding: {str(e)}{Colors.ENDC}")
            # Clean up on error
            for client in clients.values():
                await client.disconnect()
            clients = {}
    
    input("Press Enter to continue...")

# Main function
async def main():
    # Create sessions directory if not exists
    if not os.path.exists('sessions'):
        os.makedirs('sessions')
    
    # Create media directory if v2l is used
    if not os.path.exists('media'):
        os.makedirs('media')
    
    while True:
        print_header()
        print_menu()
        
        choice = input("Enter your choice: ")
        
        if choice == '1':
            await add_account()
        elif choice == '2':
            delete_account()
        elif choice == '3':
            list_accounts()
        elif choice == '4':
            await add_source()
        elif choice == '5':
            delete_source()
        elif choice == '6':
            await add_target()
        elif choice == '7':
            delete_target()
        elif choice == '8':
            list_groups()
        elif choice == '9':
            set_delay()
        elif choice == '10':
            configure_media()
        elif choice == '11':
            await toggle_forwarding()
        elif choice == '12':
            show_status()
        elif choice == '0':
            # Exit
            if config['active']:
                print(f"{Colors.WARNING}Forwarding is active. Stop forwarding before exiting? (y/n): {Colors.ENDC}")
                confirm = input()
                if confirm.lower() == 'y':
                    config['active'] = False
                    save_config(config)
                    # Disconnect all clients
                    for client in clients.values():
                        await client.disconnect()
            
            print(f"{Colors.BLUE}Goodbye!{Colors.ENDC}")
            break
        else:
            print(f"{Colors.FAIL}Invalid choice! Please try again.{Colors.ENDC}")
            input("Press Enter to continue...")

# Run the main function
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
        # Save config and disconnect clients
        if 'config' in globals() and config.get('active', False):
            config['active'] = False
            save_config(config)
            # Disconnect clients in a new event loop
            loop = asyncio.new_event_loop()
            for client in clients.values():
                loop.run_until_complete(client.disconnect())
        sys.exit(0)
