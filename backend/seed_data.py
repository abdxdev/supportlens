import json
import os
import datetime
import random

import psycopg2

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://supportlens:supportlens@localhost:5432/supportlens",
)

TRACES = [
    # --- Billing (5) ---
    {
        "user_message": "Why was I charged $49 when my plan is supposed to be $29/month?",
        "bot_response": "I apologize for the confusion! It looks like you were automatically upgraded to our Pro plan on your last billing cycle. I can reverse that upgrade and issue a $20 credit to your account right away. Would you like me to proceed?",
        "categories": ["Billing"],
        "response_time_ms": 812,
    },
    {
        "user_message": "Can you explain what the 'platform fee' line item on my invoice means?",
        "bot_response": "Great question! The platform fee is a small infrastructure charge that covers payment processing costs, data storage, and 24/7 uptime monitoring. It's a flat $2/month added to all plans. You'll see it listed separately on every invoice for transparency.",
        "categories": ["Billing"],
        "response_time_ms": 743,
    },
    {
        "user_message": "How do I update my credit card on file?",
        "bot_response": "You can update your payment method in Settings → Billing → Payment Methods. Click 'Add new card', enter your details, and set it as the default. Your next invoice will automatically charge the new card. Need help finding the settings page?",
        "categories": ["Billing"],
        "response_time_ms": 654,
    },
    {
        "user_message": "Do you offer annual billing? Is there a discount?",
        "bot_response": "Yes! Switching to annual billing saves you 20% compared to monthly. For example, the Pro plan drops from $49/month to $39/month (billed as $468/year). You can switch in Settings → Billing → Billing Cycle. The discount applies immediately on your next renewal.",
        "categories": ["Billing"],
        "response_time_ms": 920,
    },
    {
        "user_message": "What payment methods do you accept? Can I pay by bank transfer?",
        "bot_response": "We currently accept Visa, Mastercard, American Express, and Discover. Bank transfers (ACH) are available on our Enterprise plan. If you're on a lower tier and need ACH, contact our sales team — they can set up a custom arrangement for you.",
        "categories": ["Billing"],
        "response_time_ms": 689,
    },

    # --- Refund (4) ---
    {
        "user_message": "I accidentally upgraded to the Enterprise plan. I want a refund for the difference.",
        "bot_response": "I completely understand — accidents happen! Since the upgrade was within the last 24 hours, I can process a full prorated refund for the difference. I'll reverse the upgrade and issue $120 back to your original payment method within 5–7 business days. Done!",
        "categories": ["Refund"],
        "response_time_ms": 1102,
    },
    {
        "user_message": "I was double-charged this month. I need one of those charges refunded.",
        "bot_response": "I'm so sorry about that! I can see a duplicate charge of $49 on March 3rd. I've initiated a refund for the duplicate — you should see it back on your card within 3–5 business days. I've also added a note to your account to prevent this from happening again.",
        "categories": ["Refund"],
        "response_time_ms": 988,
    },
    {
        "user_message": "I signed up by mistake and want my money back. It's been 3 days.",
        "bot_response": "Not a problem! We offer a 14-day money-back guarantee for all new subscriptions. Since you're within the window, I've processed a full refund of $29. Your account will remain active until the end of the current billing period. Expect the refund in 5–7 business days.",
        "categories": ["Refund"],
        "response_time_ms": 876,
    },
    {
        "user_message": "The feature I paid for doesn't work at all. I deserve my money back.",
        "bot_response": "I sincerely apologize for the frustration! A non-functional feature is absolutely a valid reason for a refund. I'm escalating this to our engineering team and processing a partial credit of $15 for this month. Would you like a full refund instead, or should I fix the feature first?",
        "categories": ["Refund"],
        "response_time_ms": 1340,
    },

    # --- Account Access (4) ---
    {
        "user_message": "I can't log in. I keep getting 'Invalid credentials' even though my password is correct.",
        "bot_response": "Let's get you back in! First, try resetting your password using the 'Forgot Password' link on the login page. If you still can't access your account after resetting, your account may be temporarily locked after multiple failed attempts. I can manually unlock it — just confirm your registered email.",
        "categories": ["Account Access"],
        "response_time_ms": 934,
    },
    {
        "user_message": "I lost access to my authenticator app and can't get past the MFA screen.",
        "bot_response": "Don't worry — I can help you bypass MFA for account recovery. Please verify your identity by confirming your billing address and the last 4 digits of your payment method. Once verified, I'll temporarily disable MFA so you can log in and set up a new authenticator.",
        "categories": ["Account Access"],
        "response_time_ms": 1215,
    },
    {
        "user_message": "My account was suspended. I didn't receive any warning. What's going on?",
        "bot_response": "I'm sorry for the disruption! Your account was flagged by our automated fraud detection system due to an unusual login from a new location. I've reviewed it and it looks legitimate. I've reinstated your account and it should be accessible within 5 minutes.",
        "categories": ["Account Access"],
        "response_time_ms": 1455,
    },
    {
        "user_message": "I need to transfer my account to a new email address. My old one no longer exists.",
        "bot_response": "Account email transfers require identity verification for security. Please reply with your full name, company name, and the last 4 digits of your payment method. Once verified, I'll update your login email and send a confirmation to the new address. This typically takes under 10 minutes.",
        "categories": ["Account Access"],
        "response_time_ms": 1023,
    },

    # --- Cancellation (3) ---
    {
        "user_message": "I want to cancel my subscription immediately.",
        "bot_response": "I'm sorry to see you go! Before I process the cancellation, may I ask what led to this decision? If it's a pricing concern, I can offer a 30% discount for the next 3 months. If you'd still like to cancel, I can do that now — you'll retain access until the end of your current billing cycle.",
        "categories": ["Cancellation"],
        "response_time_ms": 1087,
    },
    {
        "user_message": "How do I downgrade from Pro to the free plan?",
        "bot_response": "You can downgrade in Settings → Billing → Change Plan → Free. The downgrade takes effect at the end of your current billing period, so you'll keep Pro features until then. Note that the free plan has a 100-transaction limit per month.",
        "categories": ["Cancellation"],
        "response_time_ms": 743,
    },
    {
        "user_message": "I'm closing my business and need to shut down my account entirely.",
        "bot_response": "I understand, and I'm sorry to hear that. To close your account, I'll need to cancel your subscription and delete your data per GDPR guidelines. Before proceeding, please download any invoices or reports you need. Once closed, data cannot be recovered. Shall I proceed?",
        "categories": ["Cancellation"],
        "response_time_ms": 1189,
    },

    # --- General Inquiry (4) ---
    {
        "user_message": "What's the difference between the Pro and Enterprise plans?",
        "bot_response": "Pro ($49/month) includes up to 10,000 transactions/month, advanced analytics, and email support. Enterprise (custom pricing) adds unlimited transactions, a dedicated account manager, SSO, custom integrations, and SLA guarantees. If you're processing more than 10k transactions/month, Enterprise is worth considering. Want a demo?",
        "categories": ["General Inquiry"],
        "response_time_ms": 834,
    },
    {
        "user_message": "Does Bot integrate with QuickBooks?",
        "bot_response": "Yes! Bot has a native QuickBooks Online integration available on Pro and Enterprise plans. Once connected, invoices and payments sync automatically every hour. You can set it up in Settings → Integrations → QuickBooks.",
        "categories": ["General Inquiry"],
        "response_time_ms": 712,
    },
    {
        "user_message": "Is my payment data PCI compliant? How do you store card information?",
        "bot_response": "Absolutely — Bot is PCI DSS Level 1 compliant, the highest certification available. We don't store raw card numbers on our servers. All payment data is tokenized and handled by Stripe, which is also PCI Level 1 certified.",
        "categories": ["General Inquiry"],
        "response_time_ms": 789,
    },
    {
        "user_message": "Can I export my transaction history to a spreadsheet?",
        "bot_response": "Yes! Head to Reports → Transaction History, set your date range and any filters, then click 'Export CSV'. The file downloads instantly and opens in Excel or Google Sheets. You can also schedule automated monthly exports in Settings → Reports.",
        "categories": ["General Inquiry"],
        "response_time_ms": 601,
    },

    # --- Multi-category (5) ---
    {
        "user_message": "I was charged twice last month and I want both charges reversed and then cancel my plan.",
        "bot_response": "I can see the duplicate charge and I've initiated a refund for both amounts — expect them back within 5–7 business days. I've also processed your cancellation; you'll retain access until the end of the current billing cycle. Is there anything else I can help with?",
        "categories": ["Refund", "Cancellation"],
        "response_time_ms": 1230,
    },
    {
        "user_message": "My account is locked and I also need a refund for last month since I couldn't use the service.",
        "bot_response": "I've unlocked your account — you should be able to log in right away. Regarding the refund, since the lockout prevented access for most of the billing period, I've processed a full refund of $49. I'm sorry for the trouble!",
        "categories": ["Account Access", "Refund"],
        "response_time_ms": 1415,
    },
    {
        "user_message": "I want to cancel but first I need to download my invoices and understand what I was charged for.",
        "bot_response": "Of course! Your invoices are in Settings → Billing → Invoice History — you can download each as a PDF. The charges cover your Pro plan base fee plus the $2 platform fee. Once you've downloaded everything, just let me know and I'll process the cancellation.",
        "categories": ["Cancellation", "Billing"],
        "response_time_ms": 978,
    },
    {
        "user_message": "I can't log in to check my latest invoice. Can you tell me what I was billed?",
        "bot_response": "I can see your account is temporarily locked due to multiple failed login attempts — I've unlocked it now. Your most recent invoice was $49 for the Pro plan on the 1st of this month. You can view the full breakdown in Settings → Billing once you're logged in.",
        "categories": ["Account Access", "Billing"],
        "response_time_ms": 1105,
    },
    {
        "user_message": "I need a refund for this month and I want to cancel going forward.",
        "bot_response": "I've processed a full refund for this month's charge — you should see it within 5–7 business days. I've also scheduled a cancellation at the end of the current billing period so you won't be charged again. Let me know if there's anything else!",
        "categories": ["Refund", "Cancellation"],
        "response_time_ms": 1055,
    },
]


def seed():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS traces (
            id                BIGSERIAL PRIMARY KEY,
            user_message      TEXT      NOT NULL,
            bot_response      TEXT      NOT NULL,
            category          TEXT      NOT NULL,
            timestamp         TEXT      NOT NULL,
            response_time_ms  INTEGER   NOT NULL
        )
        """
    )
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM traces")
    existing = cur.fetchone()[0]
    if existing >= len(TRACES):
        print(f"Database already has {existing} traces — skipping seed.")
        cur.close()
        conn.close()
        return

    # Spread timestamps across the last 30 days
    now = datetime.datetime.utcnow()
    for t in TRACES:
        offset_hours = random.randint(0, 30 * 24)
        ts = (now - datetime.timedelta(hours=offset_hours)).isoformat(timespec="seconds") + "Z"
        cur.execute(
            """INSERT INTO traces (user_message, bot_response, category, timestamp, response_time_ms)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                t["user_message"],
                t["bot_response"],
                json.dumps(t["categories"]),
                ts,
                t["response_time_ms"],
            ),
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"Seeded {len(TRACES)} traces successfully.")


if __name__ == "__main__":
    seed()
