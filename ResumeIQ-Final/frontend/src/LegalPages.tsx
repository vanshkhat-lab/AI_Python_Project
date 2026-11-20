import type { JSX } from "react";
import { useEffect } from "react";
import "./legal.css";

export type LegalPageKind = "privacy" | "terms" | "refunds" | "contact";

const SUPPORT_EMAIL = (import.meta.env.VITE_SUPPORT_EMAIL ?? "").trim();
const BUSINESS_ADDRESS = (import.meta.env.VITE_BUSINESS_ADDRESS ?? "").trim();
const SUPPORT_PHONE = (import.meta.env.VITE_SUPPORT_PHONE ?? "").trim();
const LAST_REVIEWED = "21 November 2026";

const paths: Record<LegalPageKind, string> = {
  privacy: "/privacy-policy",
  terms: "/terms-and-conditions",
  refunds: "/refund-and-cancellation-policy",
  contact: "/contact-us",
};

const labels: Record<LegalPageKind, string> = {
  privacy: "Privacy Policy",
  terms: "Terms & Conditions",
  refunds: "Refund & Cancellation Policy",
  contact: "Contact Us",
};

export function getLegalRoute(pathname: string): LegalPageKind | null {
  const path = pathname.replace(/\/+$/, "") || "/";
  if (path === "/privacy-policy" || path === "/privacy") return "privacy";
  if (path === "/terms-and-conditions" || path === "/terms") return "terms";
  if (path === "/refund-and-cancellation-policy" || path === "/refunds") return "refunds";
  if (path === "/contact-us" || path === "/contact") return "contact";
  return null;
}

export function LegalLinks({ className = "" }: { className?: string }) {
  return (
    <nav className={className} aria-label="Legal and support">
      <a href={paths.privacy}>Privacy Policy</a>
      <a href={paths.terms}>Terms & Conditions</a>
      <a href={paths.refunds}>Refunds & Cancellations</a>
      <a href={paths.contact}>Contact</a>
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
        <strong>Business / operating address</strong>
        <p>{BUSINESS_ADDRESS || "To be supplied before public commercial launch."}</p>
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
        This draft describes how ResumeIQ handles personal information when users access the resume
        analysis service. It must be reviewed against the production configuration and final
        business details before publication as a live policy.
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
        descriptions. Data retention, backups and deletion procedures must be verified before
        we make promises about automatic deletion.
      </p>

      <h2>4. Providers and optional AI features</h2>
      <p>
        ResumeIQ uses Netlify for frontend hosting, Render for its API, Supabase for accounts
        and credit records, and Razorpay for checkout and payment processing. If optional
        AI-generated wording suggestions are enabled and explicitly requested, resume excerpts
        and relevant analysis findings may be processed by an external AI provider. Those
        optional features should be separately explained in the interface before launch.
      </p>
      <p>
        Razorpay handles payment entry. ResumeIQ records payment references and status rather
        than collecting full card numbers or CVVs through its own forms. Provider infrastructure
        may process data in different locations; exact processing locations and transfer
        arrangements should be confirmed before live release.
      </p>

      <h2>5. Feedback visibility</h2>
      <p>
        Feedback submitted through the current customer-feedback feature is displayed to other
        visitors of the application. Do not include your email, phone number, resume details,
        banking information, or other private information in public feedback. Use the dedicated
        support contact for private questions once it has been published.
      </p>

      <h2>6. Choices, corrections and requests</h2>
      <p>
        You can update certain information through your account provider and clear browser
        session history on your device. A documented process for account deletion, data requests,
        and retention periods is still being finalized. Contact information for such requests
        must be published before accepting live customers.
      </p>

      <h2>7. Security and updates</h2>
      <p>
        ResumeIQ uses authenticated API requests and database access controls for credits and
        purchases. No online service can promise absolute security. This draft may change as
        the product, providers, and applicable requirements evolve.
      </p>
    </>
  );
}

function Terms() {
  return (
    <>
      <p>
        These draft Terms describe the intended rules for using ResumeIQ. They must be finalized
        with the verified legal operator details and reviewed before live commercial use.
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
        The current plan offers two introductory analysis credits to eligible new accounts.
        Each completed analysis consumes one credit. The proposed paid pack adds five analysis
        credits for a one-time ₹99 purchase. There is no recurring subscription in this
        version. Live purchases are not enabled yet; Razorpay Test Mode payments do not involve
        actual funds.
      </p>
      <p>
        Credits are intended for use within the account that received them. Do not attempt to
        manipulate balances, abuse introductory offers, or bypass backend restrictions.
        The final expiration, transfer and withdrawal rules must be set before live sales.
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
        When live payments become available, eligible purchases will be processed by Razorpay.
        The applicable refund and cancellation rules will be disclosed in the
        {" "}<a href={paths.refunds}>Refund & Cancellation Policy</a>{" "}
        before purchase. Statutory consumer rights are not excluded.
      </p>
      <h2>8. Legal operator and contact</h2>
      <p>
        ResumeIQ's verified legal operator, business address, support contact and final
        jurisdictional terms must be added before this draft is published for live customers.
      </p>
    </>
  );
}

function RefundPolicy() {
  return (
    <>
      <p>
        <strong>No real payments are currently accepted.</strong> The ₹99 checkout operates in
        Razorpay Test Mode. This page outlines a proposed refund procedure for future
        live credit-pack purchases and requires owner review before commercial launch.
      </p>
      <h2>1. Digital delivery</h2>
      <p>
        Credits are digital services delivered to a user's ResumeIQ account following
        verification of a successful payment. The proposed pack contains five additional
        analysis credits for ₹99 and does not ship physical goods.
      </p>
      <h2>2. Unsuccessful or duplicate charges</h2>
      <p>
        If a live payment is captured but credits are not added, or the same order is charged
        more than once, the customer should contact support with the transaction reference.
        We will investigate the payment status and provide the missing credits or an
        appropriate refund where due.
      </p>
      <h2>3. Cancellation and unused credits</h2>
      <p>
        There is no recurring subscription to cancel in the current version. A proposed
        customer-friendly approach is to accept refund requests for wholly unused credit
        packs within seven calendar days of purchase, subject to payment verification,
        applicable consumer law, and the terms displayed at the time of purchase.
        <strong> This seven-day rule is a draft proposal, not an active promise.</strong>
      </p>
      <h2>4. Used credits</h2>
      <p>
        Once credits are used to generate analyses, requests will be reviewed according to
        the nature of the issue, including duplicate charges, service failure, fraud, and
        applicable consumer rights. A final policy must not restrict refunds required by law.
      </p>
      <h2>5. How refunds will be handled</h2>
      <p>
        Customers will be able to contact the published ResumeIQ support address with their
        account email and Razorpay order or payment reference. They should never share their
        card number, CVV, OTP or banking password. Approved refunds will ordinarily be routed
        through the original payment channel; exact processing times depend on the payment
        provider and the final published policy.
      </p>
      <h2>6. Test transactions</h2>
      <p>
        Transactions completed using Razorpay Test Mode do not transfer actual money and are
        not eligible for real-money refunds. Test credits are for development and evaluation.
      </p>
    </>
  );
}

function Contact() {
  return (
    <>
      <p>
        Need help with your account, missing credits, or a payment issue? This page will hold
        ResumeIQ's verified business support details before real payments go live.
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
        application. Live checkout is currently disabled, and all payment testing uses
        Razorpay Test Mode.
      </p>
    </>
  );
}

const pageContents: Record<LegalPageKind, () => JSX.Element> = {
  privacy: PrivacyPolicy,
  terms: Terms,
  refunds: RefundPolicy,
  contact: Contact,
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
          <p>Draft prepared {LAST_REVIEWED}</p>
        </div>
        <div className="ri-legal-alert" role="note">
          <strong>Pre-launch draft — review required.</strong> These pages describe the current
          test-stage product and proposed terms. Contact details and the final policies must
          be approved before accepting real customer payments.
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
        <p>© {new Date().getFullYear()} ResumeIQ · Test-stage service</p>
        <LegalLinks className="ri-legal-links" />
      </footer>
    </div>
  );
}
