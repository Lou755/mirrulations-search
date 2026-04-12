import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getAuthStatus } from "../api/searchApi";
import "../styles/Home.css";

export default function PrivacyPolicy() {
  /** null = still checking; avoids showing “sign in” copy briefly for signed-in users */
  const [loggedIn, setLoggedIn] = useState(null);

  useEffect(() => {
    getAuthStatus()
      .then((data) => setLoggedIn(Boolean(data.logged_in)))
      .catch(() => setLoggedIn(false));
  }, []);

  return (
    <div className="legal-page">
      <header className="legal-topbar">
        <div className="legal-brand">
          <Link to="/">Mirrulations</Link>
        </div>
        <nav className="legal-nav" aria-label="Policy navigation">
          <Link className="home-btn home-btn-secondary" to="/">
            Home
          </Link>
          {loggedIn === false ? (
            <a className="home-btn home-btn-primary" href="/login">
              Sign in with Google
            </a>
          ) : null}
          {loggedIn === true ? (
            <>
              <Link className="home-btn home-btn-secondary" to="/explorer">
                Search
              </Link>
              <a className="home-btn home-btn-secondary" href="/logout">
                Sign out
              </a>
            </>
          ) : null}
        </nav>
      </header>

      <main className="legal-main">
        <h1>Privacy Policy — Mirrulations Explorer</h1>

        <div className="legal-note">
          This policy describes how Mirrulations Explorer handles information when you use our web application. It is
          intended to align with{" "}
          <a
            href="https://developers.google.com/terms/api-services-user-data-policy"
            target="_blank"
            rel="noopener noreferrer"
          >
            Google&apos;s API Services User Data Policy
          </a>{" "}
          and Limited Use requirements for data received from Google APIs.
        </div>

        <h2>1. Who we are</h2>
        <p>
          Mirrulations Explorer is a search and exploration tool for federal regulatory docket data. It is operated by
          students at Moravian University as part of a capstone project. For questions, contact Benjamin Coleman at{" "}
          <a href="mailto:colemanb@moravian.edu">colemanb@moravian.edu</a>.
        </p>

        <h2>2. Information we collect</h2>
        {loggedIn === true ? (
          <p>
            <strong>Google account.</strong> You signed in with Google. That process shares limited account information
            with us under the OAuth scopes configured for this application, currently including:
          </p>
        ) : loggedIn === false ? (
          <p>
            <strong>Google sign-in.</strong> If you choose to sign in with Google, Google shares limited account
            information with us under the OAuth scopes configured for this application, currently including:
          </p>
        ) : (
          <p>
            <strong>Google sign-in.</strong> When you use Google to sign in, Google shares limited account information
            with us under the OAuth scopes configured for this application, currently including:
          </p>
        )}
        <ul>
          <li>
            <code>openid</code> — OpenID Connect identifier for your session
          </li>
          <li>
            <code>https://www.googleapis.com/auth/userinfo.email</code> — your Google account email address
          </li>
          <li>
            <code>https://www.googleapis.com/auth/userinfo.profile</code> — your display name and related basic profile
            fields supplied by Google for that scope
          </li>
        </ul>
        <p>
          We use that information only to authenticate you, display your name in the interface, associate your activity
          with your account, and operate features you use (such as saved docket lists or download requests).
        </p>
        <p>
          <strong>Session.</strong> After you sign in, we set an HTTP-only session cookie so your browser can use the app
          without sending Google tokens on every request.
        </p>
        <p>
          <strong>What you search.</strong> Search text and filters you use are processed to show results. Do not enter
          sensitive personal information in search unless you intend for it to be processed.
        </p>

        <h2>3. How we use Google user data</h2>
        <p>We use Google user data only to:</p>
        <ul>
          <li>Identify you and keep you signed in securely;</li>
          <li>Show your name (and similar profile fields from Google) in the app;</li>
          <li>Associate saved dockets, download requests, and similar features with your account;</li>
          <li>Operate, secure, debug, and improve the features you see in Mirrulations Explorer.</li>
        </ul>
        <p>
          We do <strong>not</strong> use Google user data for advertising. We do <strong>not</strong> sell Google user
          data. We do <strong>not</strong> use it for credit or lending decisions. We do <strong>not</strong> allow people
          to read your Google account contents except for security, abuse prevention, legal compliance, or when you
          explicitly agree for a specific support request.
        </p>

        <h2>4. Limited use &amp; transfers</h2>
        <p>
          Data from Google APIs is handled according to the Google API Services User Data Policy, including Limited Use
          rules. We do not sell your Google user data. We may share it with service providers who help us run the service
          (for example, hosting), under contracts that protect your information. We may also use or disclose information
          when needed for security, to prevent abuse, or to comply with law.
        </p>

        <h2>5. Storage and retention</h2>
        <p>
          Account details (such as email and name) and data you create in the app (such as saved docket lists) may be
          kept while your account is active or as needed to provide the service. Download-related records may be kept for
          a limited time for operations. We may delete or anonymize data when we no longer need it.
        </p>

        <h2>6. Your choices</h2>
        <p>
          You can sign out using the sign-out control in the app. You can remove this app&apos;s access to your Google
          account in your Google Account security settings. That stops new sign-ins; data we already stored may remain
          until deleted under our retention practices.
        </p>

        <h2>7. Changes</h2>
        <p>
          We may update this policy when the product or legal requirements change. The current version is always the one
          posted on this page.
        </p>

        <h2>8. Contact</h2>
        <p>
          For privacy questions, contact Benjamin Coleman at{" "}
          <a href="mailto:colemanb@moravian.edu">colemanb@moravian.edu</a>.
        </p>

        <p>
          <Link to="/">Return to home</Link>
        </p>
      </main>

      <footer className="home-footer">
        <Link to="/">Home</Link>
        <span className="home-footer-sep" aria-hidden>
          ·
        </span>
        <span>Privacy Policy</span>
      </footer>
    </div>
  );
}
