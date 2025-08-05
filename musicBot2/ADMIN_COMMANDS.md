# Admin Commands Documentation

This document describes the admin commands available in the JARP Music Bot v2.

## Overview

Admin commands provide server administrators and bot owners with tools to manage the bot's operation, including updating, restarting, and monitoring system resources.

## Commands

### `!update`
**Permission Required**: Administrator role or bot owner

Updates and restarts the bot by pulling the latest changes from GitHub.

**What it does:**
1. Checks for uncommitted changes and warns the user
2. Stops existing bot processes
3. Pulls latest changes from the `main` branch
4. Updates dependencies if `requirements.txt` has changed
5. Restarts the bot in the background
6. Provides status updates throughout the process

**Usage:**
```
!update
```

**Example Response:**
```
✅ Update Complete
Bot has been successfully updated and restarted!

Output:
🔄 Starting bot update and restart process...
✅ Successfully pulled latest changes
✅ Bot started successfully (PID: 12345)
🎉 Bot update and restart completed successfully!
```

### `!restart`
**Permission Required**: Administrator role or bot owner

Restarts the bot without pulling any updates from GitHub.

**What it does:**
1. Stops existing bot processes
2. Waits for processes to fully terminate
3. Starts the bot in the background
4. Redirects output to `bot.log`

**Usage:**
```
!restart
```

**Example Response:**
```
✅ Restart Complete
Bot has been restarted successfully!
```

### `!system_status`
**Permission Required**: Administrator role or bot owner

Shows detailed system status including CPU, memory, and disk usage.

**What it shows:**
- System CPU usage percentage
- Memory usage (total, used, available)
- Disk usage percentage
- Bot process information (PID, CPU, memory usage)

**Usage:**
```
!system_status
```

**Example Response:**
```
📊 Bot System Status

🖥️ System
CPU: 15.2%
Memory: 45.8%
Disk: 67.3%

🤖 Bot Processes
PID: 12345
CPU: 2.1%
Memory: 1.8%

📈 Memory Details
Total: 16GB
Used: 7GB
Available: 9GB
```

## Permission System

### Administrator Role
Users with the "Administrator" permission in the Discord server can use all admin commands.

### Bot Owner
The bot owner (configured in the bot application) can use all admin commands regardless of server permissions.

### Permission Check
The bot checks permissions in this order:
1. Server Administrator permission
2. Bot owner status
3. Deny access if neither condition is met

## Technical Details

### Update Script
The `!update` command uses the `update_and_restart.sh` script located in the bot's root directory. This script:

- Uses colored output for better visibility
- Checks for uncommitted changes
- Safely terminates existing processes
- Pulls from the `main` branch
- Updates Python dependencies if needed
- Starts the bot with proper logging

### Process Management
- Uses `pkill` to find and terminate bot processes
- Waits for processes to fully stop before restarting
- Uses `nohup` to run the bot in the background
- Redirects output to `bot.log` for debugging

### System Monitoring
The `!status` command uses the `psutil` library to gather system information:
- CPU usage with 1-second sampling
- Virtual memory statistics
- Disk usage for the root filesystem
- Process information for bot instances

## Error Handling

### Common Issues

**Script Not Found**
```
❌ Error
Update script not found. Please check the installation.
```
*Solution*: Ensure `update_and_restart.sh` exists in the bot directory and is executable.

**Permission Denied**
```
❌ Permission Denied
You need administrator permissions or be the bot owner to use this command.
```
*Solution*: Grant the user Administrator permissions or ensure they are the bot owner.

**Update Timeout**
```
⏰ Timeout
Update process timed out. The bot may still be updating in the background.
```
*Solution*: Check the server logs or `bot.log` for detailed error information.

**psutil Not Available**
```
❌ Error
psutil library not available. Install it with: pip install psutil
```
*Solution*: Install psutil with `pip install psutil`

## Security Considerations

1. **Permission Restriction**: Only administrators and bot owners can use these commands
2. **Process Safety**: The update script includes safety checks for uncommitted changes
3. **Error Handling**: Comprehensive error handling prevents bot crashes
4. **Logging**: All operations are logged for audit purposes

## Troubleshooting

### Bot Won't Start After Update
1. Check `bot.log` for error messages
2. Verify all dependencies are installed: `pip install -r requirements.txt`
3. Ensure the bot token is correctly configured
4. Check file permissions on the update script

### Update Script Fails
1. Ensure the script is executable: `chmod +x update_and_restart.sh`
2. Check if you're in a git repository: `git status`
3. Verify network connectivity to GitHub
4. Check for uncommitted changes: `git status`

### Permission Issues
1. Verify the user has Administrator role in Discord
2. Check if the user is the bot owner
3. Ensure the bot has proper permissions in the server

## Log Files

- `bot.log`: Main bot output and error logs
- `logs/`: Detailed logging information from the logging system
- Console output: Real-time status updates during operations 