import type { JSX } from "react";
import { useEffect } from "react";
import "./legal.css";

export type LegalPageKind = "privacy" | "terms" | "refunds" | "contact" | "about" | "delivery";

const SUPPORT_EMAIL = (import.meta.env.VITE_SUPPORT_EMAIL || "ronicris1234@gmail.com").trim();
const BUSINESS_ADDRESS = "Mohali, Punjab, India";
const SUPPORT_PHONE = (import.meta.env.VITE_SUPPORT_PHONE ?? "").trim();
const LAST_REVIEWED = "24 November 2026";

const paths: Record<LegalPageKind, string> = {
  privacy: "/privacy-policy",
  terms: "/terms-and-conditions",
  refunds: "/refund-and-cancellation-policy",
  contact: "/contact-us",
  about: "/about-us",
  delivery: "/digital-delivery-policy",
};

const labels: Record<LegalPageKind, string> = {
  privacy: "Privacy Policy",
  terms: "Terms & Conditions",
  refunds: "Refund & Cancellation Policy",
  contact: "Contact Us",
  about: "About ResumeIQ",
  delivery: "Digital Delivery Policy",
};

export function getLegalRoute(pathname: string): LegalPageKind | null {
  const path = pathname.replace(/\/+$/, "") || "/";
  if (path === "/privacy-policy" || path === "/privacy") return "privacy";
  if (path === "/terms-and-conditions" || path === "/terms") return "terms";
  if (path === "/refund-and-cancellation-policy" || path === "/refunds") return "refunds";
  if (path === "/contact-us" || path === "/contact") return "contact";
  if (path === "/about-us" || path === "/about") return "about";
  if (path === "/digital-delivery-policy" || path === "/delivery") return "delivery";
  return null;
}

export function LegalLinks({ className = "" }: { className?: string }) {
  return (
    <nav className={className} aria-label="Legal and support">
      <a href={paths.privacy}>Privacy Policy</a>
      <a href={paths.terms}>Terms & Conditions</a>
      <a href={paths.refunds}>Refunds & Cancellations</a>
      <a href={paths.contact}>Contact</a>
      <a href={paths.about}>About Us</a>
      <a href={paths.delivery}>Digital Delivery</a>
    </nav>
  );
}

function ContactDetails() {
  return (
    <div className="ri-contact-details">
      <div className="ri-contact-item">
        <strong>Support email</strong>
        {SUPPORT_EMAIL ? (
          <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
        ) : (
          <p>Not yet published. A verified support email is required before live payments.</p>
        )}
      </div>
      <div className="ri-contact-item">
        <strong>Public business location</strong>
        <p>{BUSINESS_ADDRESS}</p>
      </div>
      {SUPPORT_PHONE && (
        <div className="ri-contact-item">
          <strong>Phone support</strong>
          <a href={`tel:${SUPPORT_PHONE.replace(/[^+\d]/g, "")}`}>{SUPPORT_PHONE}</a>
        </div>
      )}
    </div>
  );
}

function PrivacyPolicy() {
  return (
    <>
      <p>
        This policy explains how ResumeIQ handles information when you use our
        resume-analysis service.
      </p>

      <h2>1. Information handled by ResumeIQ</h2>
      <ul>
        <li><strong>Account details:</strong> email address, authentication identifiers, and related sign-in information managed through Supabase Authentication.</li>
        <li><strong>Resume and job description content:</strong> text or documents that you submit to receive an analysis.</li>
        <li><strong>Analysis data:</strong> match results, recommendations, and reports returned to your browser.</li>
        <li><strong>Credits and purchases:</strong> your remaining credits and payment/order references, including transaction status and amount.</li>
        <li><strong>Feedback:</strong> feedback messages you choose to submit in the application.</li>
        <li><strong>Technical information:</strong> basic logs or diagnostic information that our hosting and payment service providers may process.</li>
      </ul>

      <h2>2. How information is used</h2>
      <p>
        Information is used to create and secure accounts, provide resume-job comparisons,
        calculate and manage credits, record purchases, troubleshoot failures, and respond to
        legitimate support or payment inquiries.
      </p>

      <h2>3. Resume files and analysis history</h2>
      <p>
        The current analysis endpoint extracts resume content to generate a response. The
        signed-in frontend keeps recent report history in the browser's session storage. The
        legacy shared server-side saved-report feature is currently disabled. A browser session
        or page data may remain on your device until cleared, and hosting providers may retain
        operational logs according to their settings.
      </p>
      <p>
        Please avoid including unnecessary sensitive personal information in resumes or job
        descriptions. We do not promise automatic deletion of all provider logs or backups;
        information may be retained for operational, security or payment-record purposes.
      </p>

      <h2>4. Providers and optional AI features</h2>
      <p>
        ResumeIQ uses Netlify for frontend hosting, Render for its API, Supabase for accounts
        and credit records, and Razorpay for checkout and payment processing. If optional
        AI-generated wording suggestions are enabled and explicitly requested, resume excerpts
        and relevant analysis findings may be processed by an external AI provider. Those
        optional features are used only when available and requested through the application.
      </p>
      <p>
        Razorpay handles payment entry. ResumeIQ records payment references and status rather
        than collecting full card numbers or CVVs through its own forms. Provider infrastructure
        may process information in different locations under its own policies.
      </p>

      <h2>5. Feedback visibility</h2>
      <p>
        Feedback submitted through the current customer-feedback feature is displayed to other
        visitors of the application. Do not include your email, phone number, resume details,
        banking information, or other private information in public feedback. Use our support
        email for private questions.
      </p>

      <h2>6. Choices, corrections and requests</h2>
      <p>
        You can update certain information through your account provider and clear browser
        session history on your device. To request information access, correction or deletion,
        contact our support email. Some records may need to be retained for security,
        payment or other legitimate purposes.
      </p>

      <h2>7. Security and updates</h2>
      <p>
        ResumeIQ uses authenticated API requests and database access controls for credits and
        purchases. No online service can promise absolute security. We may update this
        policy as the product, providers, and applicable requirements evolve.
      </p>
    </>
  );
}

function Terms() {
  return (
    <>
      <p>
        These Terms describe the rules for using ResumeIQ, including one-time credit packs
        when paid checkout is available.
      </p>
      <h2>1. What ResumeIQ provides</h2>
      <p>
        ResumeIQ is an online tool that compares user-supplied resume content with job
        descriptions and provides match indications, skill-gap information and practical
        suggestions. It is not a recruitment agency, job-placement service, interview coaching
        business, or legal or professional career adviser.
      </p>
      <h2>2. Your account</h2>
      <p>
        You are responsible for using an email address you control, keeping your login
        credentials secure, and providing accurate information. You must have permission to
        upload any documents or text submitted for analysis.
      </p>
      <h2>3. Analysis limitations</h2>
      <p>
        Results are estimates based on the text provided, not a definitive assessment of an
        applicant's suitability. Match scores are not official applicant tracking system
        results and do not guarantee interviews, offers, or employment. Review all
        recommendations before using them and never add qualifications you do not possess.
      </p>
      <h2>4. Free and paid credits</h2>
      <p>
        Eligible new accounts receive two introductory analysis credits. Each completed
        analysis consumes one credit. When paid checkout is enabled, a one-time ₹99 purchase
        adds five analysis credits. This is not a recurring subscription.
      </p>
      <p>
        Credits are tied to the account that receives them. Do not attempt to manipulate
        balances, abuse introductory offers, or bypass backend restrictions. Refunds for
        unused purchased packs are governed by the refund policy.
      </p>
      <h2>5. Acceptable use</h2>
      <p>
        Do not submit content you lack permission to use, attempt unauthorized access, send
        malicious requests, interfere with the service, or publish confidential information
        through public feedback. We may restrict abusive activity as necessary to protect
        the service and its users.
      </p>
      <h2>6. Availability and changes</h2>
      <p>
        We work to maintain the service but cannot promise uninterrupted availability or
        error-free recommendations. Features and pricing may change with appropriate
        customer notice and subject to applicable legal obligations.
      </p>
      <h2>7. Payments, cancellations and refunds</h2>
      <p>
        When paid checkout is available, purchases are processed through Razorpay.
        The applicable rules are described in our{" "}
        <a href={paths.refunds}>Refund & Cancellation Policy</a>.
        Statutory consumer rights are not excluded.
      </p>
      <h2>8. Legal operator and contact</h2>
      <p>
        ResumeIQ is operated by Vansh Khatri (Individual). Public business location:
        {" "}{BUSINESS_ADDRESS}. Customer support:{" "}
        <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>.
      </p>
    </>
  );
}

function RefundPolicy() {
  return (
    <>
      <p>
        This policy applies to one-time ₹99 credit-pack purchases made through ResumeIQ
        when paid checkout is available. Test-mode transactions do not transfer real money.
      </p>

      <h2>1. Credit pack and delivery</h2>
      <p>
        A ₹99 purchase provides five additional resume-analysis credits to the purchaser's
        ResumeIQ account after successful payment verification. Credits are delivered
        digitally; there are no physical goods or shipping charges.
      </p>

      <h2>2. Refunds for wholly unused packs — 7 days</h2>
      <p>
        You may request a refund within <strong>seven calendar days of the successful
        payment</strong> if <strong>none of the five credits from that purchased pack has
        been used</strong>. Once we verify the purchase, account and unused pack status,
        an eligible refund will be approved to the original payment method. A refund request
        received after seven calendar days is not covered by this unused-pack policy,
        but statutory rights and remedies for payment or service failures still apply.
      </p>

      <h2>3. Credits already used</h2>
      <p>
        If one or more credits from the purchased pack have been used, a standard
        unused-pack refund is not available. We will review requests case by case,
        including technical failures, incorrect credit deductions, duplicate payments,
        fraud or other circumstances requiring a remedy under applicable law.
      </p>

      <h2>4. Missing credits, duplicate or unsuccessful payments</h2>
      <p>
        If money is deducted but purchased credits are not delivered, or a transaction
        is charged twice, contact us with the payment reference. We will verify the
        transaction and provide the missing credits or an appropriate refund. Failed
        or pending transactions will be handled according to their confirmed payment
        status and applicable payment-provider procedures.
      </p>

      <h2>5. Cancellation</h2>
      <p>
        ResumeIQ currently sells one-time credit packs and does not offer recurring
        subscriptions, so there is no ongoing subscription to cancel. Requests to
        reverse a completed credit-pack purchase are handled under the refund rules above.
      </p>

      <h2>6. How to request a refund</h2>
      <p>
        Email <a href="mailto:ronicris1234@gmail.com">ronicris1234@gmail.com</a> from your
        account email address, with the subject "ResumeIQ refund request" and your
        Razorpay order or payment reference, purchase date and reason for the request.
        Do not share card numbers, CVVs, OTPs or passwords. We will verify eligibility
        and, when approved, initiate the refund to the original payment method.
        Bank or payment-provider processing times may vary.
      </p>

      <h2>7. Refund processing times</h2>
      <p>
        Approved refunds are initiated to the original payment method. The time for funds
        to appear depends on the payment provider and your bank or payment method.
      </p>

      <h2>8. Consumer rights</h2>
      <p>
        This policy does not override any refunds, remedies or other rights that customers
        may be entitled to under applicable consumer protection law.
      </p>
    </>
  );
}

function Contact() {
  return (
    <>
      <p>
        Need help with your account, missing credits, or a payment issue? Contact the
        ResumeIQ support team using the details below.
      </p>
      <ContactDetails />
      <h2>When contacting support</h2>
      <p>
        Describe the issue and include your account email. For payment problems, include
        the Razorpay order or payment reference where possible. Do not share passwords,
        authentication tokens, card numbers, CVVs or one-time passwords.
      </p>
      <h2>Important: public feedback is not private support</h2>
      <p>
        The application's customer feedback section is visible to other users. Please do
        not submit private account or payment information there.
      </p>
      <h2>Service information</h2>
      <p>
        ResumeIQ provides resume-to-job matching and recommendations through a web
        application. The option to purchase credits is available only when checkout
        is enabled in the application.
      </p>
    </>
  );
}

function About() {
  return (
    <>
      <p>
        ResumeIQ is a web-based resume analysis tool designed to help job applicants understand
        how the evidence in their resume aligns with a particular job description.
      </p>
      <h2>What ResumeIQ does</h2>
      <p>
        Users upload or paste resume information and provide a job description. ResumeIQ
        compares skills and other requirements, shows evidence-based matching information,
        and suggests areas where the resume could be clearer or more complete.
      </p>
      <h2>How the service works</h2>
      <p>
        After creating an account, eligible users start with two introductory analysis
        credits. Each completed analysis consumes one credit. When checkout is enabled,
        a one-time ₹99 purchase provides five additional credits.
      </p>
      <h2>What ResumeIQ does not promise</h2>
      <p>
        ResumeIQ does not guarantee a job interview, an offer of employment, or an
        official applicant tracking system score. Its analysis is informational and
        should be reviewed by the applicant before using any recommendations.
      </p>
      <h2>Business details</h2>
      <p>
        ResumeIQ is operated by Vansh Khatri (Individual). Public business location:
        {" "}{BUSINESS_ADDRESS}. For support enquiries, see the Contact Us page.
      </p>
      <h2>Support</h2>
      <p>
        For account, credit or payment assistance, see our{" "}
        <a href={paths.contact}>Contact Us page</a>.
      </p>
    </>
  );
}

function Delivery() {
  return (
    <>
      <p>
        ResumeIQ provides a digital service only. No physical products are sold or
        shipped, and no courier delivery is required.
      </p>
      <h2>Digital delivery of credits</h2>
      <p>
        After a successful payment has been verified by our backend, the purchased
        credits are added to the customer's signed-in ResumeIQ account. The
        one-time ₹99 credit pack provides five analysis credits.
      </p>
      <h2>When will credits appear?</h2>
      <p>
        Verified payments normally trigger an automated credit update. If payment
        verification or the payment provider is delayed, credits may not appear
        immediately. Customers should check their credit balance and purchase
        status before retrying a payment.
      </p>
      <h2>Missing digital delivery</h2>
      <p>
        If a charge is completed but the credits do not appear, email{" "}
        <a href="mailto:ronicris1234@gmail.com">ronicris1234@gmail.com</a> with
        your account email and Razorpay order or payment reference. We will
        investigate and arrange missing credits or a refund where appropriate.
        Do not send full card details, passwords or OTPs.
      </p>
      <h2>No shipping or physical returns</h2>
      <p>
        Delivery is electronic to the customer's account; there are no shipping
        fees, tracking numbers, delivery addresses or physical returns. Refund
        eligibility is governed by the{" "}
        <a href={paths.refunds}>Refund & Cancellation Policy</a>.
      </p>
      <h2>Payment confirmation</h2>
      <p>
        Credits are granted only after a payment is confirmed. If a payment is incomplete,
        credits will not be added. You can check purchase status or contact support.
      </p>
    </>
  );
}

const pageContents: Record<LegalPageKind, () => JSX.Element> = {
  privacy: PrivacyPolicy,
  terms: Terms,
  refunds: RefundPolicy,
  contact: Contact,
  about: About,
  delivery: Delivery,
};

export default function LegalPage({ kind }: { kind: LegalPageKind }) {
  useEffect(() => {
    const previousTitle = document.title;
    document.title = `${labels[kind]} | ResumeIQ`;
    return () => { document.title = previousTitle; };
  }, [kind]);

  const PageContent = pageContents[kind];
  return (
    <div className="ri-legal-site">
      <header className="ri-legal-header">
        <a className="ri-legal-brand" href="/"> <span className="ri-legal-icon">R</span> Resume<span>IQ</span></a>
        <a className="ri-legal-back" href="/">← Back to ResumeIQ</a>
      </header>
      <main className="ri-legal-main">
        <div className="ri-legal-heading">
          <span className="ri-legal-kicker">RESUMEIQ · INFORMATION & SUPPORT</span>
          <h1>{labels[kind]}</h1>
          <p>Last updated: {LAST_REVIEWED}</p>
        </div>
        <article className="ri-legal-article">
          <PageContent />
        </article>
        <aside className="ri-legal-help">
          <h2>Need help?</h2>
          <p>Find business contact details and payment support information.</p>
          <a href={paths.contact}>Contact ResumeIQ →</a>
        </aside>
      </main>
      <footer className="ri-legal-footer">
        <p>© {new Date().getFullYear()} ResumeIQ · Operated by Vansh Khatri</p>
        <LegalLinks className="ri-legal-links" />
      </footer>
    </div>
  );
}
