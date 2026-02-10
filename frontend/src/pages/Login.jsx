import { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './Auth.css';

const REMEMBER_KEY = 'llm_council_remember_creds';

function getStoredCredentials() {
  try {
    const raw = localStorage.getItem(REMEMBER_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed?.email && parsed?.password) return parsed;
    return null;
  } catch {
    return null;
  }
}

function setStoredCredentials(email, password) {
  try {
    localStorage.setItem(REMEMBER_KEY, JSON.stringify({ email, password }));
  } catch {
    // ignore
  }
}

function clearStoredCredentials() {
  try {
    localStorage.removeItem(REMEMBER_KEY);
  } catch {
    // ignore
  }
}

// Icons
const BrainIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 4.5a2.5 2.5 0 0 0-4.96-.46 2.5 2.5 0 0 0-1.98 3 2.5 2.5 0 0 0-1.32 4.24 3 3 0 0 0 .34 5.58 2.5 2.5 0 0 0 2.96 3.08A2.5 2.5 0 0 0 12 19.5a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 12 4.5"/>
    <path d="m15.7 10.4-.9.4"/>
    <path d="m9.2 13.2-.9.4"/>
    <path d="m13.6 15.7-.4-.9"/>
    <path d="m10.8 9.2-.4-.9"/>
    <path d="m15.7 13.5-.9-.4"/>
    <path d="m9.2 10.9-.9-.4"/>
    <path d="m10.4 15.7.4-.9"/>
    <path d="m13.1 9.2.4-.9"/>
  </svg>
);

const EmailIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="4" width="20" height="16" rx="2" />
    <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
  </svg>
);

const LockIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
);

const EyeIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const EyeOffIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
    <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
    <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
    <line x1="2" y1="2" x2="22" y2="22" />
  </svg>
);

const AlertIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <line x1="12" y1="8" x2="12" y2="12" />
    <line x1="12" y1="16" x2="12.01" y2="16" />
  </svg>
);

const SparklesIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
    <path d="M5 3v4"/>
    <path d="M19 17v4"/>
    <path d="M3 5h4"/>
    <path d="M17 19h4"/>
  </svg>
);

const UsersIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);

const ShieldIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    <path d="m9 12 2 2 4-4"/>
  </svg>
);

const ZapIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
  </svg>
);

const ArrowRightIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 12h14"/>
    <path d="m12 5 7 7-7 7"/>
  </svg>
);

export default function Login() {
  const stored = getStoredCredentials();
  const [email, setEmail] = useState(stored?.email ?? '');
  const [password, setPassword] = useState(stored?.password ?? '');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(!!stored);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || '/';
  const hasStoredCreds = !!getStoredCredentials();

  // Pre-fill from storage on mount (in case state was reset)
  useEffect(() => {
    const s = getStoredCredentials();
    if (s && !email && !password) {
      setEmail(s.email);
      setPassword(s.password);
      setRememberMe(true);
    }
  }, []);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password);
      if (rememberMe) {
        setStoredCredentials(email, password);
      } else {
        clearStoredCredentials();
      }
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || 'Login failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickLogin = () => {
    handleSubmit(null);
  };

  const handleUseDifferentAccount = () => {
    clearStoredCredentials();
    setEmail('');
    setPassword('');
    setRememberMe(false);
    setError('');
  };

  const features = [
    { icon: UsersIcon, title: 'Multi-Model Council', desc: 'Get perspectives from multiple AI models' },
    { icon: SparklesIcon, title: 'Smart Synthesis', desc: 'AI-powered consensus building' },
    { icon: ShieldIcon, title: 'Private & Secure', desc: 'Your data stays protected' },
    { icon: ZapIcon, title: 'Lightning Fast', desc: 'Parallel processing for speed' },
  ];

  return (
    <div className="auth-page">
      {/* Left Side - Branding */}
      <div className="auth-branding">
        <div className="auth-branding-content">
          <div className="auth-brand-logo">
            <BrainIcon />
          </div>
          <h1 className="auth-brand-title">AI Konsey</h1>
          <p className="auth-brand-subtitle">Multi-LLM Deliberation System</p>

          <div className="auth-features">
            {features.map((feature, index) => (
              <div key={index} className="auth-feature" style={{ animationDelay: `${index * 0.1}s` }}>
                <div className="auth-feature-icon">
                  <feature.icon />
                </div>
                <div className="auth-feature-text">
                  <span className="auth-feature-title">{feature.title}</span>
                  <span className="auth-feature-desc">{feature.desc}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Animated Background Elements */}
        <div className="auth-bg-shapes">
          <div className="auth-shape auth-shape-1"></div>
          <div className="auth-shape auth-shape-2"></div>
          <div className="auth-shape auth-shape-3"></div>
        </div>
      </div>

      {/* Right Side - Form */}
      <div className="auth-form-section">
        <div className="auth-form-container">
          {/* Mobile Logo */}
          <div className="auth-mobile-logo">
            <div className="auth-brand-logo">
              <BrainIcon />
            </div>
            <h1>AI Konsey</h1>
          </div>

          <div className="auth-form-header">
            <h2>Welcome back</h2>
            <p>Sign in to continue to your council</p>
          </div>

          {error && (
            <div className="auth-error">
              <AlertIcon />
              <span>{error}</span>
            </div>
          )}

          {hasStoredCreds && email && password && (
            <div className="auth-quick-login">
              <button
                type="button"
                className="auth-quick-login-btn"
                onClick={handleQuickLogin}
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <span className="btn-spinner"></span>
                    <span>Signing in...</span>
                  </>
                ) : (
                  <>
                    <span>Quick login</span>
                    <ArrowRightIcon className="btn-icon" />
                  </>
                )}
              </button>
              <button
                type="button"
                className="auth-use-different"
                onClick={handleUseDifferentAccount}
                disabled={isLoading}
              >
                Use different account
              </button>
            </div>
          )}

          <form onSubmit={handleSubmit} className="auth-form">
            <div className="form-group">
              <label htmlFor="email">Email address</label>
              <div className="input-wrapper">
                <EmailIcon className="input-icon" />
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  disabled={isLoading}
                  autoComplete="email"
                />
              </div>
            </div>

            <div className="form-group">
              <div className="form-label-row">
                <label htmlFor="password">Password</label>
                <Link to="/forgot-password" className="form-link">Forgot password?</Link>
              </div>
              <div className="input-wrapper has-toggle">
                <LockIcon className="input-icon" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  disabled={isLoading}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              </div>
            </div>

            <label className="auth-remember-me">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                disabled={isLoading}
              />
              <span>Remember me (quick login next time)</span>
            </label>

            <button
              type="submit"
              className="auth-submit-btn"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <span className="btn-spinner"></span>
                  <span>Signing in...</span>
                </>
              ) : (
                <>
                  <span>Sign in</span>
                  <ArrowRightIcon className="btn-icon" />
                </>
              )}
            </button>
          </form>

          <div className="auth-footer">
            <p>
              Don't have an account?{' '}
              <Link to="/register" className="auth-link">Create one</Link>
            </p>
          </div>

          <div className="auth-trust-badges">
            <span>🔒 256-bit SSL</span>
            <span>🌍 GDPR Compliant</span>
          </div>
        </div>
      </div>
    </div>
  );
}
