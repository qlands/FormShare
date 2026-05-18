---
description: How to create a FormShare account, sign in, and recover your password.
---

# Registering and logging in

Before you can create projects or upload forms, you need a FormShare account. This page walks you through registering, signing in, and recovering a forgotten password.

{% hint style="info" %}
**Hosted vs self-hosted FormShare**: The instructions below apply to [https://formshare.org](https://formshare.org) (the hosted service) and to any self-hosted FormShare instance that allows public registration. If you are using a private FormShare installation, your administrator may have disabled public sign-up, in which case they will create your account for you.
{% endhint %}

## Create your account

From the FormShare home page, click **Sign in** at the top of the screen. On the sign-in page, click the **Sign up** button below the form. The "Join FormShare" page will appear.

To register, you need to provide the following information:

* **Full name**: The name shown on your profile and on activity logs across the projects you participate in.
* **Email**: A valid email address. FormShare uses it for password recovery and for notifications such as collaboration invitations. Two accounts cannot share the same email.
* **User name** (only if asked): A short identifier used to log in and to address you in URLs. It can contain letters (A–Z, a–z), digits (0–9), dots (`.`), and underscores (`_`) — no spaces or other special characters. It must be unique across the FormShare instance and **cannot be changed afterward**.

{% hint style="info" %}
Some FormShare instances generate the user name for you automatically from your email. If you don't see a "User name" field on the registration form, this is the case.
{% endhint %}

* **Password**: The password you will use to sign in. The password must be at most 50 characters long.
* **Password confirmation**: Type the same password again to confirm.

Click **Create an account**. If any of the fields have a problem (invalid email, mismatched password confirmation, user name with invalid characters, an email or user name already in use), FormShare will indicate the error so you can correct it.

When everything is in order, FormShare creates your account, signs you in automatically, and takes you to your [Dashboard](../fundamentals/the-dashboard.md). From there, you can start by [creating your first project](creating-your-first-project.md).

{% hint style="warning" %}
**Registration disabled?** If the "Sign up" button does not appear on the sign-in page, public registration has been turned off on this FormShare instance. Contact the administrator of the instance to request an account.
{% endhint %}

## Sign in

Once you have an account, click **Sign in** at the top of the FormShare home page. The sign-in page will appear.

To sign in, you need to provide:

* **Username or email address**: Either the user name you chose at registration or the email address attached to your account — both work.
* **Password**: The password you set at registration (or your most recent password if you have changed it).

Click **Sign in**. FormShare will take you to your [Dashboard](../fundamentals/the-dashboard.md).

{% hint style="info" %}
**Different sign-in pages**: This page describes the sign-in page for FormShare account holders (people who create and manage projects). [Assistants](../fundamentals/tasks/) and [partners](../fundamentals/partners.md) sign in through their own dedicated pages, with separate URLs and credentials. If you are an assistant or a partner, ask the project owner for the correct sign-in link.
{% endhint %}

### Sign out

To sign out, click your name at the top-right of any FormShare page and choose **Sign out**. FormShare will end your session and return you to the home page.

## Forgot your password?

If you have forgotten your password, you can request a reset link by email.

On the sign-in page, click the **Forgot password?** link. The "Reset my password" page will appear.

Type your **username or email address** and click **Reset**. If your account exists, FormShare will send a password-reset email to the address on file. The email contains a link that takes you to a page where you can set a new password.

The reset link is valid for a limited time. If it expires before you use it, repeat the procedure to request a new one.

{% hint style="warning" %}
**Email recovery disabled?** Password recovery by email is only available on FormShare instances that have an outgoing mail server configured. If the "Forgot password?" link does not appear on the sign-in page, contact the administrator of the instance to reset your password manually.
{% endhint %}

{% hint style="info" %}
**Password rules**: When you set a new password (either at registration or after a reset), it must be at most 50 characters long. There is no minimum length enforced by FormShare itself, but we recommend a strong password — long, mixed-case, with digits and symbols — particularly if your account manages projects with sensitive data.
{% endhint %}

Once your password is changed, you can [sign in](#sign-in) with the new password as usual.
