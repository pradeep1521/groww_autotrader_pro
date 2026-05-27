"""Email & SMS Alerts - Risk notifications via email and SMS."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class EmailAlertService:
    """Send email alerts for trading events."""
    
    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587,
                 sender_email: str = None, sender_password: str = None):
        """
        Initialize email service.
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP port (587 for TLS)
            sender_email: Gmail address
            sender_password: Gmail app password (not regular password)
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email or "your_email@gmail.com"
        self.sender_password = sender_password or "your_app_password"
    
    def send_order_alert(self, recipient: str, order_data: Dict[str, Any]) -> bool:
        """Send order execution alert."""
        subject = f"⚡ Order Executed: {order_data.get('symbol')} {order_data.get('side')}"
        
        body = f"""
        <html>
        <body>
            <h2>Order Executed</h2>
            <table border="1" cellpadding="10">
                <tr><td><b>Symbol</b></td><td>{order_data.get('symbol')}</td></tr>
                <tr><td><b>Side</b></td><td>{order_data.get('side')}</td></tr>
                <tr><td><b>Quantity</b></td><td>{order_data.get('quantity')}</td></tr>
                <tr><td><b>Price</b></td><td>₹{order_data.get('price', 0):.2f}</td></tr>
                <tr><td><b>Order Type</b></td><td>{order_data.get('order_type')}</td></tr>
                <tr><td><b>Time</b></td><td>{order_data.get('timestamp', datetime.now())}</td></tr>
            </table>
        </body>
        </html>
        """
        
        return self._send_email(recipient, subject, body)
    
    def send_risk_alert(self, recipient: str, risk_event: Dict[str, Any]) -> bool:
        """Send risk breach alert."""
        subject = f"⚠️ Risk Alert: {risk_event.get('event_type')}"
        
        body = f"""
        <html>
        <body>
            <h2 style="color: red;">RISK ALERT</h2>
            <h3>{risk_event.get('event_type')}</h3>
            <p><b>Severity:</b> {risk_event.get('severity')}</p>
            <p><b>Message:</b> {risk_event.get('message')}</p>
            <p><b>Metrics:</b></p>
            <pre>{risk_event.get('metrics')}</pre>
            <p><b>Time:</b> {risk_event.get('timestamp', datetime.now())}</p>
        </body>
        </html>
        """
        
        return self._send_email(recipient, subject, body)
    
    def send_daily_pnl_alert(self, recipient: str, pnl_summary: Dict[str, Any]) -> bool:
        """Send daily P&L summary."""
        subject = f"📊 Daily P&L Summary - ₹{pnl_summary.get('total_pnl', 0):.0f}"
        
        body = f"""
        <html>
        <body>
            <h2>Daily Trading Summary</h2>
            <table border="1" cellpadding="10">
                <tr style="background-color: #f0f0f0;">
                    <td><b>Metric</b></td><td><b>Value</b></td>
                </tr>
                <tr><td>Total P&L</td><td style="color: {'green' if pnl_summary.get('total_pnl', 0) > 0 else 'red'}">₹{pnl_summary.get('total_pnl', 0):.2f}</td></tr>
                <tr><td>Win Rate</td><td>{pnl_summary.get('win_rate', 0):.1f}%</td></tr>
                <tr><td>Total Trades</td><td>{pnl_summary.get('total_trades', 0)}</td></tr>
                <tr><td>Profit Factor</td><td>{pnl_summary.get('profit_factor', 0):.2f}</td></tr>
                <tr><td>Max Drawdown</td><td>{pnl_summary.get('max_drawdown', 0):.2f}%</td></tr>
            </table>
            <p><b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </body>
        </html>
        """
        
        return self._send_email(recipient, subject, body)
    
    def _send_email(self, recipient: str, subject: str, body: str) -> bool:
        """Internal method to send email."""
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = recipient
            
            # Attach HTML content
            message.attach(MIMEText(body, "html"))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient, message.as_string())
            
            logger.info(f"✅ Email sent to {recipient}: {subject}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Email error: {e}")
            return False

class SMSAlertService:
    """Send SMS alerts using Twilio."""
    
    def __init__(self, account_sid: str = None, auth_token: str = None, 
                 from_number: str = None):
        """
        Initialize SMS service.
        
        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            from_number: Twilio phone number
        """
        self.account_sid = account_sid or "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
        self.auth_token = auth_token or "your_auth_token"
        self.from_number = from_number or "+1234567890"
        
        try:
            from twilio.rest import Client
            self.client = Client(self.account_sid, self.auth_token)
            self.twilio_available = True
        except ImportError:
            logger.warning("twilio not installed. Install: pip install twilio")
            self.twilio_available = False
    
    def send_order_sms(self, phone_number: str, order_data: Dict[str, Any]) -> bool:
        """Send order execution SMS."""
        message = f"🎯 {order_data.get('symbol')} {order_data.get('side')} {order_data.get('quantity')} @ ₹{order_data.get('price'):.2f}"
        
        return self._send_sms(phone_number, message)
    
    def send_risk_sms(self, phone_number: str, risk_event: Dict[str, Any]) -> bool:
        """Send risk alert SMS."""
        message = f"⚠️ {risk_event.get('event_type')}: {risk_event.get('message')[:50]}"
        
        return self._send_sms(phone_number, message)
    
    def send_daily_pnl_sms(self, phone_number: str, pnl: float, trades: int) -> bool:
        """Send daily P&L SMS."""
        symbol = "✅" if pnl >= 0 else "❌"
        message = f"{symbol} Daily: ₹{pnl:.0f} ({trades} trades)"
        
        return self._send_sms(phone_number, message)
    
    def _send_sms(self, phone_number: str, message: str) -> bool:
        """Internal method to send SMS."""
        if not self.twilio_available:
            logger.warning("Twilio not available - mock SMS")
            logger.info(f"📱 [MOCK SMS] to {phone_number}: {message}")
            return True
        
        try:
            sms = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=phone_number
            )
            
            logger.info(f"✅ SMS sent to {phone_number}: {message}")
            return True
        
        except Exception as e:
            logger.error(f"❌ SMS error: {e}")
            return False

class AlertManager:
    """Unified alert management for multiple channels."""
    
    def __init__(self, email_service: EmailAlertService = None,
                 sms_service: SMSAlertService = None):
        self.email = email_service
        self.sms = sms_service
        self.alert_log = []
    
    def send_order_alert(self, event: Dict[str, Any], 
                        email_recipients: List[str] = None,
                        sms_recipients: List[str] = None) -> Dict[str, bool]:
        """Send order alert to all channels."""
        results = {}
        
        # Email alerts
        if email_recipients and self.email:
            for recipient in email_recipients:
                results[f"email_{recipient}"] = self.email.send_order_alert(recipient, event)
        
        # SMS alerts
        if sms_recipients and self.sms:
            for phone in sms_recipients:
                results[f"sms_{phone}"] = self.sms.send_order_sms(phone, event)
        
        self.alert_log.append({
            'type': 'order',
            'event': event,
            'results': results,
            'timestamp': datetime.now()
        })
        
        return results
    
    def send_risk_alert(self, risk_event: Dict[str, Any],
                       email_recipients: List[str] = None,
                       sms_recipients: List[str] = None) -> Dict[str, bool]:
        """Send risk alert to all channels."""
        results = {}
        
        # Email alerts
        if email_recipients and self.email:
            for recipient in email_recipients:
                results[f"email_{recipient}"] = self.email.send_risk_alert(recipient, risk_event)
        
        # SMS alerts
        if sms_recipients and self.sms:
            for phone in sms_recipients:
                results[f"sms_{phone}"] = self.sms.send_risk_sms(phone, risk_event)
        
        self.alert_log.append({
            'type': 'risk',
            'event': risk_event,
            'results': results,
            'timestamp': datetime.now()
        })
        
        return results
    
    def send_daily_summary(self, pnl_summary: Dict[str, Any],
                          email_recipients: List[str] = None,
                          sms_recipients: List[str] = None) -> Dict[str, bool]:
        """Send daily summary to all channels."""
        results = {}
        
        # Email alerts
        if email_recipients and self.email:
            for recipient in email_recipients:
                results[f"email_{recipient}"] = self.email.send_daily_pnl_alert(recipient, pnl_summary)
        
        # SMS alerts
        if sms_recipients and self.sms:
            for phone in sms_recipients:
                results[f"sms_{phone}"] = self.sms.send_daily_pnl_sms(phone, 
                                                                      pnl_summary.get('total_pnl', 0),
                                                                      pnl_summary.get('total_trades', 0))
        
        return results

# Example usage
def example_alerts():
    """Example alert configuration."""
    
    # Initialize services
    email_service = EmailAlertService(
        sender_email="your_email@gmail.com",
        sender_password="your_app_password"  # Use app-specific password for Gmail
    )
    
    sms_service = SMSAlertService(
        account_sid="ACXXXXXXX",
        auth_token="your_token",
        from_number="+1234567890"
    )
    
    alert_manager = AlertManager(email_service, sms_service)
    
    # Example: Order execution alert
    order_event = {
        'symbol': 'NIFTY50',
        'side': 'BUY',
        'quantity': 1,
        'price': 23894.10,
        'order_type': 'MARKET',
        'timestamp': datetime.now()
    }
    
    results = alert_manager.send_order_alert(
        order_event,
        email_recipients=['trader@example.com'],
        sms_recipients=['+919876543210']
    )
    
    print("✅ Alert results:", results)

if __name__ == "__main__":
    example_alerts()
