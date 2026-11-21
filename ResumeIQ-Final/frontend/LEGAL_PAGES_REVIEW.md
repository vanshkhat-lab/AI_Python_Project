# ResumeIQ public policies — launch review checklist

The branch `feature/resumeiq-homepage` now includes public routes:

- `/privacy-policy`
- `/terms-and-conditions`
- `/refund-and-cancellation-policy`
- `/contact-us`
- `/about-us`
- `/digital-delivery-policy`

They are accessible even when the visitor is signed out. The public homepage and signed-in
dashboard link to them, and `frontend/public/_redirects` supports direct URL loads on Netlify.

## Required before accepting live payments

These are **DRAFT** policies, not legal advice and not a substitute for review.

1. The public About Us and Digital Delivery pages have been added as pre-launch drafts.
   Confirm the legal operator/business identity on About Us before accepting real payments.
2. The approved customer-support address `ronicris1234@gmail.com` is included as the
   page's default; `VITE_SUPPORT_EMAIL` can override it on Netlify. Confirm the
   mailbox is actively monitored.
3. Verify the business operating address and, if appropriate, configure
   `VITE_BUSINESS_ADDRESS`. It will be displayed to the public as submitted.
4. If publishing a support telephone number, configure `VITE_SUPPORT_PHONE` only
   if calls will be handled on that line.
5. Identify the legal owner/operator and add the appropriate merchant name/address,
   jurisdiction and grievance/contact details.
6. The owner has approved a **seven-calendar-day refund window for wholly unused credit packs**.
   Confirm that the payment/credit ledger can identify whether credits from a particular
   purchased pack have been used, and establish a real support and refund-fulfilment workflow.
   The wording remains marked for pre-launch legal and operational review, particularly
   for technical failures, duplicate charges, customer rights and account closures.
7. Confirm actual data processing, cookies, deletion/retention, logging and backups,
   optional AI features, vendor details and support for account deletion requests.
8. Verify whether any statutory notices or consents are needed based on your customers
   and location, and obtain qualified legal review as appropriate.
9. Keep the TEST MODE disclosure until Razorpay production activation is completed and
   all real-payment flows have been secured and tested.
10. Test all six URLs directly in a fresh browser tab, with and without an authenticated session.
11. Build and check locally with `npm run build` before merging or changing Netlify deployment branches.

These environment variables are **public-facing** because they are compiled into the
Vite frontend bundle. Never put API secrets, personal banking details, or credentials into
`VITE_...` variables.

## Credit-pack refund eligibility: current technical limitation

The current `credit_purchases` records identify a purchase, customer, five-credit grant,
and payment reference. The `analysis_credit_transactions` table records deductions
against the user's shared balance. **These records are not linked to an individual
purchased pack**, so the system cannot reliably prove whether a specific pack's five
credits have been entirely unused (especially if a customer has free credits or buys
multiple packs). Before enabling live transactions, implement purchase-level credit
allocation/consumption and a tested refund/reversal workflow, ensuring each refunded
pack can be refunded once and that consumed credits cannot be inadvertently refunded.

Do not change the currently working test-mode accounting SQL or payments backend based
only on a public-facing policy update. Stage, migrate, test, and reconcile this change
separately before live checkout.
