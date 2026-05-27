"""Telegram Bot - Real-time trading updates via Telegram."""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramTradingBot:
    """Telegram bot for trading position tracking and alerts."""
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        Initialize Telegram bot.
        
        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Your Telegram chat ID
        """
        self.bot_token = bot_token or "YOUR_BOT_TOKEN"
        self.chat_id = chat_id or "YOUR_CHAT_ID"
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        try:
            import requests
            self.requests = requests
            self.available = True
        except ImportError:
            logger.warning("requests not installed. Install: pip install requests")
            self.available = False
    
    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send plain text message."""
        if not self.available:
            logger.warning("Telegram not available - mock mode")
            logger.info(f"📱 [Telegram] {text}")
            return True
        
        try:
            url = f"{self.api_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            response = self.requests.post(url, json=payload)
            
            if response.status_code == 200:
                logger.info(f"✅ Telegram message sent")
                return True
            else:
                logger.error(f"Telegram error: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False
    
    def send_position_update(self, position: Dict[str, Any]) -> bool:
        """Send position update."""
        symbol = position.get('symbol', 'N/A')
        side = position.get('side', 'N/A')
        qty = position.get('quantity', 0)
        entry = position.get('entry_price', 0)
        current = position.get('current_price', 0)
        pnl = position.get('pnl', 0)
        pnl_pct = position.get('pnl_pct', 0)
        
        pnl_emoji = "✅" if pnl >= 0 else "❌"
        
        message = f"""
📈 <b>Position Update</b>

<b>Symbol:</b> {symbol}
<b>Side:</b> {side}
<b>Quantity:</b> {qty}
<b>Entry:</b> ₹{entry:.2f}
<b>Current:</b> ₹{current:.2f}
<b>P&L:</b> {pnl_emoji} ₹{pnl:.2f} ({pnl_pct:+.2f}%)

<i>{datetime.now().strftime('%H:%M:%S')}</i>
        """
        
        return self.send_message(message)
    
    def send_order_status(self, order: Dict[str, Any]) -> bool:
        """Send order execution status."""
        symbol = order.get('symbol', 'N/A')
        side = order.get('side', 'N/A')
        qty = order.get('quantity', 0)
        price = order.get('price', 0)
        status = order.get('status', 'UNKNOWN')
        
        status_emoji = "✅" if status == "FILLED" else "⏳" if status == "PENDING" else "❌"
        
        message = f"""
{status_emoji} <b>Order {status}</b>

<b>Symbol:</b> {symbol}
<b>Side:</b> {side}
<b>Quantity:</b> {qty}
<b>Price:</b> ₹{price:.2f}
<b>Status:</b> {status}

<i>{datetime.now().strftime('%H:%M:%S')}</i>
        """
        
        return self.send_message(message)
    
    def send_daily_summary(self, summary: Dict[str, Any]) -> bool:
        """Send daily trading summary."""
        pnl = summary.get('total_pnl', 0)
        trades = summary.get('total_trades', 0)
        win_rate = summary.get('win_rate', 0)
        profit_factor = summary.get('profit_factor', 0)
        max_dd = summary.get('max_drawdown', 0)
        
        pnl_emoji = "✅" if pnl >= 0 else "❌"
        
        message = f"""
📊 <b>Daily Summary</b>

<b>Total P&L:</b> {pnl_emoji} ₹{pnl:,.2f}
<b>Total Trades:</b> {trades}
<b>Win Rate:</b> {win_rate:.1f}%
<b>Profit Factor:</b> {profit_factor:.2f}
<b>Max Drawdown:</b> {max_dd:.2f}%

<i>Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
        """
        
        return self.send_message(message)
    
    def send_alert(self, alert_type: str, message: str) -> bool:
        """Send alert with emoji."""
        alert_emojis = {
            'risk': '⚠️',
            'warning': '🔔',
            'error': '❌',
            'success': '✅',
            'info': 'ℹ️'
        }
        
        emoji = alert_emojis.get(alert_type, '🔔')
        
        text = f"""
{emoji} <b>{alert_type.upper()}</b>

{message}

<i>{datetime.now().strftime('%H:%M:%S')}</i>
        """
        
        return self.send_message(text)
    
    def send_portfolio_snapshot(self, portfolio: Dict[str, Any]) -> bool:
        """Send portfolio snapshot with all positions."""
        positions = portfolio.get('positions', [])
        total_value = portfolio.get('total_value', 0)
        cash = portfolio.get('cash', 0)
        pnl = portfolio.get('total_pnl', 0)
        
        pnl_emoji = "✅" if pnl >= 0 else "❌"
        
        positions_text = ""
        for pos in positions[:5]:  # Show top 5 positions
            symbol = pos.get('symbol', 'N/A')
            qty = pos.get('quantity', 0)
            current_price = pos.get('current_price', 0)
            pos_pnl = pos.get('pnl', 0)
            positions_text += f"\n  {symbol}: {qty} @ ₹{current_price:.2f} ({pos_pnl:+.0f})"
        
        if len(positions) > 5:
            positions_text += f"\n  ... +{len(positions) - 5} more"
        
        message = f"""
💼 <b>Portfolio Snapshot</b>

<b>Total Value:</b> ₹{total_value:,.2f}
<b>Cash:</b> ₹{cash:,.2f}
<b>Total P&L:</b> {pnl_emoji} ₹{pnl:,.2f}

<b>Open Positions:</b>{positions_text}

<i>{datetime.now().strftime('%H:%M:%S')}</i>
        """
        
        return self.send_message(message)
    
    def send_performance_chart_link(self, chart_url: str) -> bool:
        """Send performance chart image."""
        message = f"""
📈 <b>Performance Chart</b>

<a href="{chart_url}">View Chart</a>

<i>{datetime.now().strftime('%H:%M:%S')}</i>
        """
        
        return self.send_message(message)

class TelegramCommandHandler:
    """Handle Telegram bot commands."""
    
    def __init__(self, bot: TelegramTradingBot):
        self.bot = bot
        self.commands = {
            '/positions': self.cmd_positions,
            '/pnl': self.cmd_pnl,
            '/summary': self.cmd_summary,
            '/help': self.cmd_help,
            '/status': self.cmd_status
        }
    
    def cmd_positions(self, args: str = None) -> str:
        """Show current positions."""
        return "📈 Current Positions:\n1. NIFTY50 BUY 1 @ ₹23,894\n2. TCS BUY 10 @ ₹3,850"
    
    def cmd_pnl(self, args: str = None) -> str:
        """Show P&L."""
        return "💰 Daily P&L: ₹12,345 (5 trades, 80% win rate)"
    
    def cmd_summary(self, args: str = None) -> str:
        """Show trading summary."""
        return """
📊 Trading Summary:
• Total Trades: 5
• Win Rate: 80%
• Profit Factor: 2.5
• Max Drawdown: 2.1%
• Best Trade: ₹5,000
• Worst Trade: -₹2,000
        """
    
    def cmd_help(self, args: str = None) -> str:
        """Show help."""
        return """
🤖 <b>Available Commands:</b>

/positions - Show open positions
/pnl - Show daily P&L
/summary - Show trading summary
/status - Show system status
/help - Show this help
        """
    
    def cmd_status(self, args: str = None) -> str:
        """Show system status."""
        return """
✅ <b>System Status:</b>

Database: Connected ✅
Broker API: Connected ✅
Risk Monitor: Active ✅
Data Feed: Streaming ✅
        """
    
    def process_command(self, command: str) -> str:
        """Process incoming command."""
        parts = command.split(' ', 1)
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else None
        
        handler = self.commands.get(cmd)
        if handler:
            return handler(args)
        else:
            return f"Unknown command: {cmd}. Type /help for available commands."

# Example usage
def example_telegram_bot():
    """Example Telegram bot usage."""
    
    # Initialize bot
    bot = TelegramTradingBot(
        bot_token="YOUR_BOT_TOKEN",
        chat_id="YOUR_CHAT_ID"
    )
    
    # Send position update
    position = {
        'symbol': 'NIFTY50',
        'side': 'BUY',
        'quantity': 1,
        'entry_price': 23850.00,
        'current_price': 23894.10,
        'pnl': 44.10,
        'pnl_pct': 0.185
    }
    
    print("Sending position update...")
    bot.send_position_update(position)
    
    # Send daily summary
    summary = {
        'total_pnl': 12345,
        'total_trades': 5,
        'win_rate': 80,
        'profit_factor': 2.5,
        'max_drawdown': 2.1
    }
    
    print("Sending daily summary...")
    bot.send_daily_summary(summary)
    
    # Command handler
    handler = TelegramCommandHandler(bot)
    print("Processing /positions command...")
    result = handler.process_command('/positions')
    print(result)

if __name__ == "__main__":
    example_telegram_bot()
