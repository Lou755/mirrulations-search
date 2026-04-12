import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "motion/react";
import { getAuthStatus } from "../api/searchApi";
import "../styles/Home.css";

import hero from "../assets/hero.jpg";

const MotionLink = motion.create(Link);

const navVariants = {
  hidden: { y: -100, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: { type: "spring", stiffness: 260, damping: 28 },
  },
};

const heroContainerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.14, delayChildren: 0.15 },
  },
};

const heroItemVariants = {
  hidden: { opacity: 0, y: 28 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", stiffness: 220, damping: 22 },
  },
};

const sectionVariants = {
  hidden: { opacity: 0, y: 40 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] },
  },
};

const buttonMotion = {
  rest: { scale: 1 },
  hover: { scale: 1.04, transition: { type: "spring", stiffness: 400, damping: 18 } },
  tap: { scale: 0.97 },
};

const cardReveal = {
  hidden: { opacity: 0, y: 20 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.06, duration: 0.45, ease: [0.22, 1, 0.36, 1] },
  }),
};

export default function Home() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    getAuthStatus()
      .then((data) => {
        if (data.logged_in) {
          setUser({ name: data.name, email: data.email });
        }
      })
      .finally(() => setAuthLoading(false));
  }, []);

  return (
    <div className="home-page">
      <motion.header
        className="home-navbar"
        role="banner"
        variants={navVariants}
        initial="hidden"
        animate="visible"
      >
        <MotionLink to="/" className="home-nav-brand">
          Mirrulations
        </MotionLink>
        <nav className="home-nav-links" aria-label="Main navigation">
          <motion.a href="#about" className="home-nav-link" whileHover={{ y: -1 }} whileTap={{ scale: 0.98 }}>
            About
          </motion.a>
          <motion.a href="#features" className="home-nav-link" whileHover={{ y: -1 }} whileTap={{ scale: 0.98 }}>
            Features
          </motion.a>
          <MotionLink to="/explorer" className="home-nav-link" whileHover={{ y: -1 }} whileTap={{ scale: 0.98 }}>
            Search
          </MotionLink>
          <MotionLink to="/privacy" className="home-nav-link" whileHover={{ y: -1 }} whileTap={{ scale: 0.98 }}>
            Privacy Policy
          </MotionLink>
          {!authLoading && user ? (
            <>
              <span className="home-nav-user" title={user.email}>
                {user.name}
              </span>
              <motion.a href="/logout" className="home-nav-link home-nav-link--ghost" whileHover={{ y: -1 }} whileTap={{ scale: 0.98 }}>
                Sign out
              </motion.a>
            </>
          ) : (
            <motion.a href="/login" className="home-nav-google" whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
              <span className="home-nav-google-icon" aria-hidden>
                <svg viewBox="0 0 24 24" width={18} height={18}>
                  <path fill="#EA4335" d="M12 5.04c1.55 0 2.96.54 4.07 1.6l3.03-3.03C17.5 2.32 14.9 1 12 1 7.58 1 3.84 3.47 2.1 7.05l3.51 2.72A6.98 6.98 0 0 1 12 5.04z" />
                  <path fill="#4285F4" d="M22.5 12.23c0-.82-.07-1.6-.22-2.36H12v4.51h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.09-1.92 3.22-4.74 3.22-8.23z" />
                  <path fill="#FBBC05" d="M5.61 14.08A7.02 7.02 0 0 1 5.04 12c0-.72.13-1.41.35-2.08L2.1 7.05A11.95 11.95 0 0 0 1 12c0 1.93.46 3.76 1.27 5.38l3.34-2.6z" />
                  <path fill="#34A853" d="M12 23c3.24 0 5.97-1.08 7.96-2.93l-3.57-2.77c-.99.67-2.26 1.07-4.39 1.07-2.39 0-4.42-.81-5.89-2.18l-3.51 2.72C6.97 21.16 9.24 23 12 23z" />
                </svg>
              </span>
              Sign in with Google
            </motion.a>
          )}
        </nav>
      </motion.header>

      <section
        className="home-hero"
        style={{
          backgroundImage: `linear-gradient(120deg, rgba(15,23,42,0.78) 0%, rgba(30,27,75,0.58) 45%, rgba(15,23,42,0.4) 100%), url(${hero})`,
        }}
      >
        <motion.div
          className="hero-text-container"
          variants={heroContainerVariants}
          initial="hidden"
          animate="visible"
        >
          <motion.h1 className="hero-title" variants={heroItemVariants}>
            Search U.S. federal
            <br />
            <span className="hero-title-accent">regulatory dockets</span>
          </motion.h1>
          <motion.p className="hero-lead" variants={heroItemVariants}>
            Mirrulations Explorer helps you find rulemakings and related documents from public U.S. federal sources. Sign
            in to search, save dockets you care about, and use downloads when your administrator enables them.
          </motion.p>
          <motion.div className="hero-buttons" variants={heroItemVariants}>
            <MotionLink
              to="/explorer"
              className="hero-btn hero-btn--primary"
              variants={buttonMotion}
              initial="rest"
              whileHover="hover"
              whileTap="tap"
            >
              Get started
            </MotionLink>
            <MotionLink
              to="/privacy"
              className="hero-btn hero-btn--outline"
              variants={buttonMotion}
              initial="rest"
              whileHover="hover"
              whileTap="tap"
            >
              Privacy Policy
            </MotionLink>
          </motion.div>
        </motion.div>
      </section>

      <motion.main
        className="home-body"
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-60px" }}
        variants={sectionVariants}
      >
        <section id="about" className="home-section home-section--narrow">
          <motion.h2 className="home-section-heading" initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.4 }}>
            What this is
          </motion.h2>
          <motion.p className="home-section-lead" initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ delay: 0.05, duration: 0.45 }}>
            A straightforward way to explore federal docket data: search by keywords and filters, open dockets and
            documents, and keep a personal list when you are signed in.
          </motion.p>
        </section>

        <section id="features" className="home-section home-section--wide">
          <motion.h2 className="home-section-heading home-section-heading--center" initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.4 }}>
            What you can do
          </motion.h2>
          <div className="home-feature-grid">
            {[
              {
                title: "Search and filter",
                body: "Find dockets and documents with text search and options such as agency, date range, and status.",
              },
              {
                title: "Save what you follow",
                body: "When you are signed in, you can keep dockets in your account so you can return to them later.",
              },
              {
                title: "Stay in control",
                body: "We only use your Google account to sign you in and run the features you use. See the Privacy Policy for details.",
              },
            ].map((card, i) => (
              <motion.article key={card.title} className="home-feature-card" custom={i} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-30px" }} variants={cardReveal}>
                <h3>{card.title}</h3>
                <p>{card.body}</p>
              </motion.article>
            ))}
          </div>
        </section>

        <section className="home-section home-section--wide">
          <motion.div className="home-cta-card" initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5 }}>
            <h2>Ready to search?</h2>
            {!authLoading && user ? (
              <>
                <p>You are signed in. Open search to look up dockets and documents.</p>
                <div className="home-cta-row">
                  <MotionLink to="/explorer" className="home-cta-primary" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                    Search Tool
                  </MotionLink>
                  <MotionLink to="/privacy" className="home-cta-secondary" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                    Privacy Policy
                  </MotionLink>
                </div>
              </>
            ) : (
              <>
                <p>Sign in with Google to open the search experience.</p>
                <div className="home-cta-row">
                  <MotionLink to="/login" className="home-cta-primary" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                    Sign in
                  </MotionLink>
                  <MotionLink to="/privacy" className="home-cta-secondary" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                    Privacy Policy
                  </MotionLink>
                </div>
              </>
            )}
          </motion.div>
        </section>

        <motion.footer className="home-page-footer" initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ duration: 0.45 }}>
          <span>Mirrulations Explorer</span>
          <span className="home-page-footer-dot" aria-hidden>
            ·
          </span>
          <Link to="/privacy">Privacy Policy</Link>
        </motion.footer>
      </motion.main>
    </div>
  );
}
