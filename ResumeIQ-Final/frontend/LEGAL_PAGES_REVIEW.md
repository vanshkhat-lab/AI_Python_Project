# ResumeIQ public policies — launch review checklist

The branch `feature/resumeiq-homepage` now includes public routes:

- `/privacy-policy`
- `/terms-and-conditions`
- `/refund-and-cancellation-policy`
- `/contact-us`

They are accessible even when the visitor is signed out. The public homepage and signed-in
dashboard link to them, and `frontend/public/_redirects` supports direct URL loads on Netlify.

## Required before accepting live payments

These are **DRAFT** policies, not legal advice and not a substitute for review.

1. Add the actual support email as a Netlify frontend environment variable:
   `VITE_SUPPORT_EMAIL` (example format only: `support@YOUR_DOMAIN`).
   You must operate the mailbox; do not configure an address that doesn't receive messages.
2. Verify the business operating address and, if appropriate, configure
   `VITE_BUSINESS_ADDRESS`. It will be displayed to the public as submitted.
3. If publishing a support telephone number, configure `VITE_SUPPORT_PHONE` only
   if calls will be handled on that line.
4. Identify the legal owner/operator and add the appropriate merchant name/address,
   jurisdiction and grievance/contact details.
5. Review the proposed **seven-day refund rule** and set a final documented policy
   for unused and used credits, technical failures, duplicate charges, refund requests,
   and account closures. Do not promise processes you cannot perform.
6. Confirm actual data processing, cookies, deletion/retention, logging and backups,
   optional AI features, vendor details and support for account deletion requests.
7. Verify whether any statutory notices or consents are needed based on your customers
   and location, and obtain qualified legal review as appropriate.
8. Keep the TEST MODE disclosure until Razorpay production activation is completed and
   all real-payment flows have been secured and tested.
9. Test all four URLs directly in a fresh browser tab, with and without an authenticated session.
10. Build and check locally with `npm run build` before merging or changing Netlify deployment branches.

These environment variables are **public-facing** because they are compiled into the
Vite frontend bundle. Never put API secrets, personal banking details, or credentials into
`VITE_...` variables.
