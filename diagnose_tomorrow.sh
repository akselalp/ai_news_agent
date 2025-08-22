#!/bin/bash

echo "🔍 DIAGNOSING TOMORROW'S FAILURE (if any)"
echo "=========================================="
echo ""

# Get current time
CURRENT_TIME=$(date)
echo "📅 Current time: $CURRENT_TIME"
echo ""

# 1. Check LaunchAgent status
echo "1. 🚀 LaunchAgent Status:"
if launchctl list | grep -q "ai-news-agent"; then
    echo "   ✅ LaunchAgent is loaded"
    PID=$(launchctl list | grep "ai-news-agent" | awk '{print $1}')
    echo "   📊 PID: $PID"
else
    echo "   ❌ LaunchAgent NOT loaded - this is the problem!"
fi

# 2. Check if any process is running
echo ""
echo "2. 📅 Running Processes:"
if ps aux | grep -q "daily_scheduler" | grep -v grep; then
    echo "   ✅ Daily scheduler process found"
    ps aux | grep "daily_scheduler" | grep -v grep
else
    echo "   ❌ No daily_scheduler process running"
fi

# 3. Check system logs for LaunchAgent activity
echo ""
echo "3. 📋 System Logs (LaunchAgent activity):"
echo "   Checking system.log for LaunchAgent entries..."
if log show --predicate 'process == "launchd"' --last 1h | grep -i "ai-news" | tail -5; then
    echo "   ✅ LaunchAgent activity found in system logs"
else
    echo "   ❌ No LaunchAgent activity in system logs"
fi

# 4. Check our specific log files
echo ""
echo "4. 📝 Our Log Files:"
if [ -f "scheduler_output.log" ]; then
    echo "   ✅ scheduler_output.log exists"
    echo "   📊 Last 5 entries:"
    tail -5 scheduler_output.log
else
    echo "   ❌ scheduler_output.log missing"
fi

if [ -f "scheduler_error.log" ]; then
    echo "   ✅ scheduler_error.log exists"
    echo "   📊 Last 5 entries:"
    tail -5 scheduler_error.log
else
    echo "   ❌ scheduler_error.log missing"
fi

# 5. Check LaunchAgent configuration
echo ""
echo "5. ⚙️  LaunchAgent Configuration:"
if [ -f ~/Library/LaunchAgents/com.user.ai-news-agent.plist ]; then
    echo "   ✅ Plist file exists"
    
    # Check Wake key
    if grep -q "<key>Wake</key>" ~/Library/LaunchAgents/com.user.ai-news-agent.plist; then
        echo "   ✅ Wake: true configured"
    else
        echo "   ❌ Wake key missing!"
    fi
    
    # Check StartCalendarInterval
    if grep -q "StartCalendarInterval" ~/Library/LaunchAgents/com.user.ai-news-agent.plist; then
        echo "   ✅ StartCalendarInterval configured"
    else
        echo "   ❌ StartCalendarInterval missing!"
    fi
else
    echo "   ❌ Plist file missing!"
fi

# 6. Test manual execution
echo ""
echo "6. 🧪 Manual Execution Test:"
echo "   Testing if the command works manually..."
if /Users/aksela/anaconda3/envs/llm_env/bin/python3 -c "print('✅ Python environment working')" 2>/dev/null; then
    echo "   ✅ Python environment accessible"
else
    echo "   ❌ Python environment failed"
fi

# 7. Immediate fix recommendations
echo ""
echo "🚨 IMMEDIATE FIX OPTIONS:"
echo "========================"
echo ""

if ! launchctl list | grep -q "ai-news-agent"; then
    echo "❌ PROBLEM: LaunchAgent not loaded"
    echo "💡 SOLUTION: Run: launchctl load ~/Library/LaunchAgents/com.user.ai-news-agent.plist"
    echo ""
fi

if ! ps aux | grep -q "daily_scheduler" | grep -v grep; then
    echo "❌ PROBLEM: No scheduler process running"
    echo "💡 SOLUTION: The LaunchAgent should start it automatically"
    echo ""
fi

echo "🔧 ALTERNATIVE SOLUTIONS:"
echo "1. Switch to crontab with wake capability"
echo "2. Use a different LaunchAgent configuration"
echo "3. Implement a hybrid solution"
echo ""

echo "📞 NEXT STEPS:"
echo "1. Run this script tomorrow at 9:15 AM if no notification"
echo "2. Send me the output"
echo "3. I'll implement the appropriate fix immediately"
echo ""
echo "💯 COMMITMENT: If tomorrow fails, I'll fix it within 1 hour"
