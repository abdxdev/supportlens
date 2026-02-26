"""
Seed the SupportLens database with 25 pre-classified traces.
Run once:  python seed_data.py
"""

import sqlite3
import uuid
import datetime
import os
import random

DB_PATH = os.path.join(os.path.dirname(__file__), "supportlens.db")

TRACES = [
    # --- Billing (6) ---
    {
        "user_message": "Why was I charged $49 when my plan is supposed to be $29/month?",
        "bot_response": "I apologize for the confusion! It looks like you were automatically upgraded to our Pro plan on your last billing cycle. I can reverse that upgrade and issue a $20 credit to your account right away. Would you like me to proceed?",
        "category": "Billing",
        "response_time_ms": 812,
    },
    {
        "user_message": "Can you explain what the 'platform fee' line item on my invoice means?",
        "bot_response": "Great question! The platform fee is a small infrastructure charge that covers payment processing costs, data storage, and 24/7 uptime monitoring. It's a flat $2/month added to all plans. You'll see it listed separately on every invoice for transparency.",
        "category": "Billing",
        "response_time_ms": 743,
    },
    {
        "user_message": "How do I update my credit card on file?",
        "bot_response": "You can update your payment method in Settings → Billing → Payment Methods. Click 'Add new card', enter your details, and set it as the default. Your next invoice will automatically charge the new card. Need help finding the settings page?",
        "category": "Billing",
        "response_time_ms": 654,
    },
    {
        "user_message": "Do you offer annual billing? Is there a discount?",
        "bot_response": "Yes! Switching to annual billing saves you 20% compared to monthly. For example, the Pro plan drops from $49/month to $39/month (billed as $468/year). You can switch in Settings → Billing → Billing Cycle. The discount applies immediately on your next renewal.",
        "category": "Billing",
        "response_time_ms": 920,
    },
    {
        "user_message": "I need a copy of my last 3 invoices for my accountant.",
        "bot_response": "No problem! All your invoices are available in Settings → Billing → Invoice History. You can download each one as a PDF. If you need them emailed to a specific address, just let me know and I'll send them over right away.",
        "category": "Billing",
        "response_time_ms": 578,
    },
    {
        "user_message": "What payment methods do you accept? Can I pay by bank transfer?",
        "bot_response": "We currently accept Visa, Mastercard, American Express, and Discover. Bank transfers (ACH) are available on our Enterprise plan. If you're on a lower tier and need ACH, contact our sales team — they can set up a custom arrangement for you.",
        "category": "Billing",
        "response_time_ms": 689,
    },

    # --- Refund (5) ---
    {
        "user_message": "I accidentally upgraded to the Enterprise plan. I want a refund for the difference.",
        "bot_response": "I completely understand — accidents happen! Since the upgrade was within the last 24 hours, I can process a full prorated refund for the difference. I'll reverse the upgrade and issue $120 back to your original payment method within 5–7 business days. Done!",
        "category": "Refund",
        "response_time_ms": 1102,
    },
    {
        "user_message": "I was double-charged this month. I need one of those charges refunded.",
        "bot_response": "I'm so sorry about that! I can see a duplicate charge of $49 on March 3rd. I've initiated a refund for the duplicate — you should see it back on your card within 3–5 business days. I've also added a note to your account to prevent this from happening again.",
        "category": "Refund",
        "response_time_ms": 988,
    },
    {
        "user_message": "I signed up by mistake and want my money back. It's been 3 days.",
        "bot_response": "Not a problem! We offer a 14-day money-back guarantee for all new subscriptions. Since you're within the window, I've processed a full refund of $29. Your account will remain active until the end of the current billing period. Expect the refund in 5–7 business days.",
        "category": "Refund",
        "response_time_ms": 876,
    },
    {
        "user_message": "The feature I paid for doesn't work at all. I deserve my money back.",
        "bot_response": "I sincerely apologize for the frustration! A non-functional feature is absolutely a valid reason for a refund. I'm escalating this to our engineering team and processing a partial credit of $15 for this month. Would you like a full refund instead, or should I fix the feature first?",
        "category": "Refund",
        "response_time_ms": 1340,
    },
    {
        "user_message": "Can I get a refund for the unused days left in my subscription?",
        "bot_response": "We do offer prorated refunds when canceling mid-cycle on annual plans. For monthly plans, we don't refund partial months, but your service continues until the period ends. Since you're on an annual plan, I can calculate your prorated refund — would you like me to proceed?",
        "category": "Refund",
        "response_time_ms": 765,
    },

    # --- Account Access (5) ---
    {
        "user_message": "I can't log in. I keep getting 'Invalid credentials' even though my password is correct.",
        "bot_response": "Let's get you back in! First, try resetting your password using the 'Forgot Password' link on the login page. If you still can't access your account after resetting, your account may be temporarily locked after multiple failed attempts. I can manually unlock it — just confirm your registered email.",
        "category": "Account Access",
        "response_time_ms": 934,
    },
    {
        "user_message": "I lost access to my authenticator app and can't get past the MFA screen.",
        "bot_response": "Don't worry — I can help you bypass MFA for account recovery. Please verify your identity by confirming your billing address and the last 4 digits of your payment method. Once verified, I'll temporarily disable MFA so you can log in and set up a new authenticator.",
        "category": "Account Access",
        "response_time_ms": 1215,
    },
    {
        "user_message": "My account was suspended. I didn't receive any warning. What's going on?",
        "bot_response": "I'm sorry for the disruption! Your account was flagged by our automated fraud detection system due to an unusual login from a new location. I've reviewed it and it looks legitimate. I've reinstated your account and it should be accessible within 5 minutes. Please let me know if you have any issues.",
        "category": "Account Access",
        "response_time_ms": 1455,
    },
    {
        "user_message": "How do I reset my password? I never received the reset email.",
        "bot_response": "Let's troubleshoot! First, check your spam/junk folder for an email from noreply@bot.io. If it's not there, the email may have been blocked. Try whitelisting our domain and click 'Resend reset email'. Alternatively, I can send the reset link to an alternate email — do you have one on file?",
        "category": "Account Access",
        "response_time_ms": 802,
    },
    {
        "user_message": "I need to transfer my account to a new email address. My old one no longer exists.",
        "bot_response": "Account email transfers require identity verification for security. Please reply with your full name, company name, and the last 4 digits of your payment method. Once verified, I'll update your login email and send a confirmation to the new address. This typically takes under 10 minutes.",
        "category": "Account Access",
        "response_time_ms": 1023,
    },

    # --- Cancellation (4) ---
    {
        "user_message": "I want to cancel my subscription immediately.",
        "bot_response": "I'm sorry to see you go! Before I process the cancellation, may I ask what led to this decision? If it's a pricing concern, I can offer a 30% discount for the next 3 months. If you'd still like to cancel, I can do that now — you'll retain access until the end of your current billing cycle.",
        "category": "Cancellation",
        "response_time_ms": 1087,
    },
    {
        "user_message": "How do I downgrade from Pro to the free plan?",
        "bot_response": "You can downgrade in Settings → Billing → Change Plan → Free. The downgrade takes effect at the end of your current billing period, so you'll keep Pro features until then. Note that the free plan has a 100-transaction limit per month. Would you like me to walk you through what changes?",
        "category": "Cancellation",
        "response_time_ms": 743,
    },
    {
        "user_message": "I'm closing my business and need to shut down my Bot account entirely.",
        "bot_response": "I understand, and I'm sorry to hear that. To close your account, I'll need to cancel your subscription and delete your data per GDPR guidelines. Before proceeding, please download any invoices or reports you need. Once I close the account, data cannot be recovered. Shall I proceed?",
        "category": "Cancellation",
        "response_time_ms": 1189,
    },
    {
        "user_message": "I don't use Bot enough to justify the cost. Can I pause instead of cancel?",
        "bot_response": "Great news — we do offer a Pause option! You can pause your subscription for up to 3 months at a reduced rate of $9/month. During the pause, your data is preserved and you can reactivate instantly. This might be a better fit than canceling. Want me to activate a pause for you?",
        "category": "Cancellation",
        "response_time_ms": 956,
    },

    # --- General Inquiry (5) ---
    {
        "user_message": "What's the difference between the Pro and Enterprise plans?",
        "bot_response": "Great question! Pro ($49/month) includes up to 10,000 transactions/month, advanced analytics, and email support. Enterprise (custom pricing) adds unlimited transactions, a dedicated account manager, SSO, custom integrations, and SLA guarantees. If you're processing more than 10k transactions/month, Enterprise is worth considering. Want a demo?",
        "category": "General Inquiry",
        "response_time_ms": 834,
    },
    {
        "user_message": "Does Bot integrate with QuickBooks?",
        "bot_response": "Yes! Bot has a native QuickBooks Online integration available on Pro and Enterprise plans. Once connected, invoices and payments sync automatically every hour. You can set it up in Settings → Integrations → QuickBooks. If you're on the Starter plan, the integration isn't available but you can export CSV reports for manual import.",
        "category": "General Inquiry",
        "response_time_ms": 712,
    },
    {
        "user_message": "How do I invite a team member to my account?",
        "bot_response": "Sure! Go to Settings → Team → Invite Member, enter their email, and assign a role (Admin, Billing Manager, or Viewer). They'll get an email invite with a link to set up their login. Pro plan supports up to 5 team members; Enterprise is unlimited. Let me know if the invite doesn't arrive!",
        "category": "General Inquiry",
        "response_time_ms": 645,
    },
    {
        "user_message": "Is my payment data PCI compliant? How do you store card information?",
        "bot_response": "Absolutely — Bot is PCI DSS Level 1 compliant, the highest certification available. We don't store raw card numbers on our servers. All payment data is tokenized and handled by Stripe, our payment processor, which is also PCI Level 1 certified. Your customers' data is safe with us.",
        "category": "General Inquiry",
        "response_time_ms": 789,
    },
    {
        "user_message": "Can I export my transaction history to a spreadsheet?",
        "bot_response": "Yes! Head to Reports → Transaction History, set your date range and any filters, then click 'Export CSV' in the top right. The file downloads instantly and opens in Excel or Google Sheets. You can also schedule automated monthly exports to be emailed to you — find that option in Settings → Reports.",
        "category": "General Inquiry",
        "response_time_ms": 601,
    },
]


def seed():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS traces (
            id                TEXT    PRIMARY KEY,
            user_message      TEXT    NOT NULL,
            bot_response      TEXT    NOT NULL,
            category          TEXT    NOT NULL,
            timestamp         TEXT    NOT NULL,
            response_time_ms  INTEGER NOT NULL
        )
        """
    )

    existing = conn.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
    if existing >= len(TRACES):
        print(f"Database already has {existing} traces — skipping seed.")
        conn.close()
        return

    # Spread timestamps across the last 30 days
    now = datetime.datetime.utcnow()
    for i, t in enumerate(TRACES):
        offset_hours = random.randint(0, 30 * 24)
        ts = (now - datetime.timedelta(hours=offset_hours)).isoformat(timespec="seconds") + "Z"
        conn.execute(
            "INSERT OR IGNORE INTO traces VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                t["user_message"],
                t["bot_response"],
                t["category"],
                ts,
                t["response_time_ms"],
            ),
        )

    conn.commit()
    conn.close()
    print(f"Seeded {len(TRACES)} traces successfully.")


if __name__ == "__main__":
    seed()
