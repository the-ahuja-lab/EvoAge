import datetime
import logging
from pathlib import Path

from fastapi.exceptions import HTTPException
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from pydantic import EmailStr
from starlette import status

from app.models.user import (
    UserPublic,  # Assuming UserPublic contains non-sensitive info
)
from app.utils.environment import CONFIG

logger = logging.getLogger(__name__)

conf = ConnectionConfig(
    MAIL_USERNAME=CONFIG.MAIL.USERNAME,
    MAIL_PASSWORD=CONFIG.MAIL.PASSWORD,
    MAIL_FROM=CONFIG.MAIL.FROM,
    MAIL_PORT=CONFIG.MAIL.PORT,
    MAIL_SERVER=CONFIG.MAIL.SERVER,
    MAIL_FROM_NAME=CONFIG.MAIL.FROM_NAME,
    MAIL_STARTTLS=CONFIG.MAIL.STARTTLS,
    MAIL_SSL_TLS=CONFIG.MAIL.SSL_TLS,
    USE_CREDENTIALS=CONFIG.MAIL.USE_CREDENTIALS,
    VALIDATE_CERTS=CONFIG.MAIL.VALIDATE_CERTS,
)

fm = FastMail(conf)


async def send_welcome_email(email_to: EmailStr):
    """Sends a welcome email to the new user."""
    subject = "Welcome to EvoKG!"
    current_year = datetime.datetime.now().year  # Get current year

    # Define the path to the logo image relative to this file
    logo_path = Path(__file__).parent.parent / "data" / "logo.png"
    logo_cid = "logo_welcome"  # Use a different CID to avoid conflicts

    # Create a beautiful HTML body
    body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f8f9fa;
            }}
            .container {{
                max-width: 600px;
                margin: 30px auto;
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 8px rgba(0,0,0,0.05);
            }}
            .header {{
                background-color: #4a90e2; /* A slightly softer blue */
                color: #ffffff;
                padding: 20px 30px;
                text-align: center;
                border-bottom: 1px solid #357abd;
            }}
            .header img.logo {{
                max-height: 50px;
                margin-bottom: 15px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: 600;
            }}
            .content {{
                padding: 35px 45px;
                line-height: 1.7;
                color: #343a40;
            }}
            .content p {{
                margin-bottom: 20px;
            }}
            .footer {{
                text-align: center;
                padding: 25px;
                font-size: 13px;
                color: #6c757d;
                background-color: #e9ecef;
                border-top: 1px solid #dee2e6;
            }}
            .footer p {{
                margin: 5px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="cid:{logo_cid}" alt="EvoKG Logo" class="logo">
                <h1>{subject}</h1>
            </div>
            <div class="content">
                <p>Dear User,</p>
                <p>Welcome to EvoKG! We are thrilled to have you on board.</p>
                <p>EvoKG is a platform designed to help you explore and understand complex knowledge graphs. We hope you find it useful and insightful.</p>
                <p>If you have any questions or need assistance, please don't hesitate to reach out to our support team.</p>
                <p>Best regards,<br><strong>The EvoKG Team</strong></p>
            </div>
            <div class="footer">
                <p>&copy; {current_year} EvoKG. All rights reserved.</p>
                <p>This is an automated message. Please do not reply directly to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    attachments = []
    if logo_path.is_file():
        attachments.append(
            {
                "file": str(logo_path.resolve()),
                "headers": {
                    "Content-ID": f"<{logo_cid}>",
                    "Content-Disposition": "inline",
                },
                "mime_type": "image",
                "mime_subtype": "png",
            }
        )
    else:
        logger.warning(
            f"Logo file not found at {logo_path}. Welcome email will be sent without logo."
        )

    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        body=body,
        subtype="html",
        attachments=attachments,
    )

    try:
        await fm.send_message(message)
        logger.info(f"Welcome email sent to {email_to}")
    except Exception as e:
        logger.error(f"Failed to send welcome email to {email_to}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send welcome email.",
        )


async def send_new_user_notification(user: UserPublic):
    """Sends an email notification to the admin about a new user signup."""
    if not CONFIG.MAIL.ADMIN_EMAIL:
        logger.warning(
            "ADMIN_EMAIL not set in MAIL config. Skipping new user notification."
        )
        return

    subject = "New User Registration Notification"
    current_year = datetime.datetime.now().year  # Get current year

    # Define the path to the logo image relative to this file
    logo_path = Path(__file__).parent.parent / "data" / "logo.png"
    logo_cid = "logo"

    # Create a more professional HTML body
    body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; /* Keep professional font */
                margin: 0;
                padding: 0;
                background-color: #f8f9fa; /* Lighter background */
            }}
            .container {{
                max-width: 600px;
                margin: 30px auto; /* More margin */
                background-color: #ffffff;
                border: 1px solid #dee2e6; /* Softer border */
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 8px rgba(0,0,0,0.05); /* Softer shadow */
            }}
            .header {{
                background-color: #4a90e2; /* A slightly softer blue */
                color: #ffffff;
                padding: 20px 30px; /* Adjusted padding */
                text-align: center;
                border-bottom: 1px solid #357abd; /* Matching border */
            }}
            .header img.logo {{ /* Style for logo */
                max-height: 50px; /* Adjust as needed */
                margin-bottom: 15px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px; /* Slightly smaller */
                font-weight: 600;
            }}
            .content {{
                padding: 35px 45px; /* Adjusted padding */
                line-height: 1.7;
                color: #343a40; /* Darker grey for text */
            }}
            .content p {{
                margin-bottom: 20px; /* Adjusted spacing */
            }}
            .user-details {{
                background-color: #f1f3f5; /* Very light grey */
                border: 1px solid #e9ecef; /* Lighter border */
                padding: 20px 25px; /* Adjusted padding */
                border-radius: 6px;
                margin-top: 20px;
                margin-bottom: 30px; /* More space below */
            }}
            .user-details ul {{
                list-style: none;
                padding: 0;
                margin: 0;
            }}
            .user-details li {{
                margin-bottom: 14px; /* Adjusted spacing */
                font-size: 15px;
            }}
            .user-details li:last-child {{
                margin-bottom: 0;
            }}
            .user-details li strong {{
                display: inline-block;
                width: 100px; /* Adjusted width */
                color: #495057;
                font-weight: 600;
                margin-right: 10px; /* Add spacing */
            }}
            .footer {{
                text-align: center;
                padding: 25px; /* More padding */
                font-size: 13px;
                color: #6c757d;
                background-color: #e9ecef;
                border-top: 1px solid #dee2e6;
            }}
            .footer p {{
                margin: 5px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="cid:{logo_cid}" alt="Company Logo" class="logo">
                <h1>{subject}</h1>
            </div>
            <div class="content">
                <p>Dear Administrator,</p>
                <p>A new user account has been successfully created on the platform. Please find the registration details below:</p>
                <div class="user-details">
                    <ul>
                        <li><strong>Username:</strong> {user.username}</li>
                        <li><strong>Email:</strong> {user.email}</li>
                        <li><strong>First Name:</strong> {user.first_name}</li>
                        <li><strong>Last Name:</strong> {user.last_name}</li>
                        <li><strong>Organization:</strong> {user.organization}</li>
                    </ul>
                </div>
                <p>You may need to review or take action regarding this new registration.</p>
                <p>Best regards,<br><strong>System Notification Service</strong></p>
            </div>
            <div class="footer">
                <p>&copy; {current_year} EvoLLM. All rights reserved.</p>
                <p>This is an automated notification. Please do not reply directly to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Prepare the attachment
    attachments = []
    if logo_path.is_file():
        attachments.append(
            {
                "file": str(logo_path.resolve()),
                "headers": {
                    "Content-ID": f"<{logo_cid}>",
                    "Content-Disposition": "inline",  # Ensure it's treated as inline
                },
                "mime_type": "image",  # Specify base mime type
                "mime_subtype": "png",  # Specify subtype
            }
        )
    else:
        logger.warning(
            f"Logo file not found at {logo_path}. Email will be sent without logo."
        )

    message = MessageSchema(
        subject=subject,
        recipients=[CONFIG.MAIL.ADMIN_EMAIL],
        body=body,
        subtype="html",
        attachments=attachments,  # Add attachments here
    )

    try:
        await fm.send_message(message)
        logger.info(
            f"New user notification sent to {CONFIG.MAIL.ADMIN_EMAIL} for user {user.username}"
        )
    except Exception as e:
        logger.error(f"Failed to send new user notification email: {e}")
