console.log("APP.JS STARTING");
const { useState, useEffect, useRef } = React;

function Input({ icon, type, placeholder, name, value, onChange }) {
    return (
        <div className="input-group">
            <input
                className="input-field"
                type={type}
                placeholder={placeholder}
                name={name}
                value={value}
                onChange={onChange}
                required
            />
            <i className={`fas ${icon} input-icon`}></i>
        </div>
    );
}

function TopAlert({ message, type }) {
    if (!message) return null;
    const style = {
        padding: '0.75rem',
        borderRadius: '8px',
        marginBottom: '1.5rem',
        fontSize: '0.9rem',
        textAlign: 'center',
        background: type === 'error' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(34, 197, 94, 0.1)',
        border: `1px solid ${type === 'error' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(34, 197, 94, 0.3)'}`,
        color: type === 'error' ? '#fca5a5' : '#86efac'
    };
    return <div style={style}>{message}</div>;
}

function OTPPopup({ email, onVerify, onResend, onCancel }) {
    const [otp, setOtp] = useState(['', '', '', '', '', '']);
    const inputs = useRef([]);

    const handleChange = (e, index) => {
        const val = e.target.value;
        if (isNaN(val)) return;

        const newOtp = [...otp];
        newOtp[index] = val.substring(val.length - 1);
        setOtp(newOtp);

        // Move to next input
        if (val && index < 5) {
            inputs.current[index + 1].focus();
        }
    };

    const handleKeyDown = (e, index) => {
        if (e.key === 'Backspace' && !otp[index] && index > 0) {
            inputs.current[index - 1].focus();
        }
    };

    const handleVerifyCode = () => {
        const code = otp.join('');
        if (code.length === 6) {
            onVerify(code);
        } else {
            alert('Please enter a 6-digit code');
        }
    };

    return (
        <div className="overlay" style={{ animation: 'fadeIn 0.3s forwards' }}>
            <div className="otp-popup">
                <i className="fas fa-shield-halved otp-icon"></i>
                <h3>Authenticate OTP</h3>
                <p>We've sent a 6-digit verification code to <br /><strong>{email || 'your email'}</strong></p>

                <div className="otp-inputs">
                    {otp.map((digit, index) => (
                        <input
                            key={index}
                            type="text"
                            maxLength="1"
                            className="otp-digit"
                            value={digit}
                            onChange={(e) => handleChange(e, index)}
                            onKeyDown={(e) => handleKeyDown(e, index)}
                            ref={(el) => (inputs.current[index] = el)}
                        />
                    ))}
                </div>

                {/* BIG Button for submit */}
                <button className="btn btn-primary" onClick={handleVerifyCode} style={{ padding: '1.2rem', fontSize: '1.1rem' }}>
                    <i className="fas fa-check-circle"></i> Verify Content
                </button>

                {/* SMALL Button to resend */}
                <button className="btn-resend" onClick={onResend}>
                    Didn't receive it? Resend OTP
                </button>

                <div style={{ marginTop: '1.5rem', cursor: 'pointer', color: 'var(--text-muted)', fontSize: '0.8rem' }} onClick={onCancel}>
                    <i className="fas fa-arrow-left"></i> Back to sign in
                </div>
            </div>
        </div>
    );
}

function AuthApp({ onLogin, toggleTheme, isDarkMode }) {
    const [view, setView] = useState('login'); // 'login' or 'register'
    const [showOTP, setShowOTP] = useState(false);
    const [formData, setFormData] = useState({ name: '', email: '', password: '' });
    const [loading, setLoading] = useState(false);
    const [alertMsg, setAlertMsg] = useState({ text: '', type: '' });

    const handleInput = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleRegisterSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setAlertMsg({ text: '', type: '' });

        try {
            const res = await fetch('/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    full_name: formData.name,
                    email: formData.email,
                    password: formData.password
                })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Registration failed');

            setAlertMsg({ text: data.message, type: 'success' });
            setShowOTP(true);
        } catch (err) {
            setAlertMsg({ text: err.message, type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleLoginSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setAlertMsg({ text: '', type: '' });

        try {
            const res = await fetch('/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: formData.email,
                    password: formData.password
                })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Login failed');

            localStorage.setItem('bowen_token', data.access_token);
            setAlertMsg({ text: 'Login successful! Redirecting...', type: 'success' });

            setTimeout(() => {
                onLogin(data.access_token);
            }, 1000);
        } catch (err) {
            if (err.message.includes('verify your email') || err.message.includes('OTP')) {
                setShowOTP(true);
                setAlertMsg({ text: err.message, type: 'error' });
            } else {
                setAlertMsg({ text: err.message, type: 'error' });
            }
        } finally {
            setLoading(false);
        }
    };

    const handleVerifyOTP = async (code) => {
        setLoading(true);
        try {
            const res = await fetch('/auth/verify-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: formData.email,
                    otp_code: code
                })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Verification failed');

            setShowOTP(false);
            setView('login');
            setAlertMsg({ text: 'Account verified successfully! Please log in.', type: 'success' });
        } catch (err) {
            alert(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleForgotPasswordSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setAlertMsg({ text: '', type: '' });
        try {
            const res = await fetch('/auth/forgot-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: formData.email })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Request failed');

            setAlertMsg({ text: data.message, type: 'success' });
            setView('resetPassword');
        } catch (err) {
            setAlertMsg({ text: err.message, type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleResetPasswordSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setAlertMsg({ text: '', type: '' });
        try {
            const res = await fetch('/auth/reset-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: formData.email,
                    otp_code: formData.otp_code,
                    new_password: formData.new_password
                })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Reset failed');

            setAlertMsg({ text: data.message + ' Please log in.', type: 'success' });
            setView('login');
        } catch (err) {
            setAlertMsg({ text: err.message, type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleSocialLogin = async (providerType) => {
        setLoading(true);
        setAlertMsg({ text: '', type: '' });

        // REAL CONFIG - from Firebase Console
        const firebaseConfig = {
            apiKey: "AIzaSyCVr89Gbx76jG9V12Hh_wrb6b5b5o5PB-0",
            authDomain: "bowen-assistant-2ab72.firebaseapp.com",
            projectId: "bowen-assistant-2ab72",
            storageBucket: "bowen-assistant-2ab72.firebasestorage.app",
            messagingSenderId: "129461512801",
            appId: "1:129461512801:web:625d1f4bbd2b5efa985820"
        };

        if (!window.firebase.apps.length) {
            window.firebase.initializeApp(firebaseConfig);
        }

        try {
            const provider = new window.firebase.auth.GoogleAuthProvider();

            const result = await window.firebase.auth().signInWithPopup(provider);
            const idToken = await result.user.getIdToken();

            const res = await fetch('/auth/social-login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ firebase_id_token: idToken })
            });
            const data = await res.json();

            if (!res.ok) throw new Error(data.detail || 'Social Login failed');

            if (data.requires_otp) {
                setFormData({ ...formData, email: result.user.email });
                setShowOTP(true);
                setAlertMsg({ text: data.message, type: 'success' });
            } else {
                localStorage.setItem('bowen_token', data.access_token);
                setAlertMsg({ text: 'Social Login successful! Redirecting...', type: 'success' });
                setTimeout(() => { onLogin(data.access_token); }, 1000);
            }
        } catch (err) {
            console.error(err);
            if (err.code !== 'auth/popup-closed-by-user') {
                setAlertMsg({ text: err.message || 'Firebase Auth failed.', type: 'error' });
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ position: 'relative', width: '100vw', display: 'flex', justifyContent: 'center' }}>
            <button className="theme-toggle" onClick={toggleTheme} type="button">
                <i className={`fas ${isDarkMode ? 'fa-sun' : 'fa-moon'}`}></i>
            </button>
            {/* The main authentication card */}
            <div className="glass-card" key={view}>
                <div className="card-header">
                    <h2 className="card-title">
                        {view === 'login' ? 'Welcome Back' :
                            view === 'register' ? 'Create Account' :
                                view === 'forgotPassword' ? 'Reset Password' : 'New Password'}
                    </h2>
                    <p className="card-subtitle">
                        {view === 'login'
                            ? 'Enter your credentials to access Bowen AI'
                            : view === 'register'
                                ? 'Join our cutting-edge AI platform today'
                                : view === 'forgotPassword'
                                    ? 'Enter your email to receive a reset code'
                                    : 'Enter the OTP and your new password'}
                    </p>
                </div>

                <TopAlert message={alertMsg.text} type={alertMsg.type} />

                {view === 'login' && (
                    <form onSubmit={handleLoginSubmit}>
                        <Input icon="fa-envelope" type="email" placeholder="Email Address" name="email" value={formData.email} onChange={handleInput} />
                        <Input icon="fa-lock" type="password" placeholder="Password" name="password" value={formData.password} onChange={handleInput} />

                        <div style={{ textAlign: 'right', marginBottom: '1.5rem', fontSize: '0.85rem' }}>
                            <span style={{ color: 'var(--text-muted)', cursor: 'pointer' }} onClick={() => { setView('forgotPassword'); setAlertMsg({ text: '', type: '' }); }}>Forgot password?</span>
                        </div>

                        <button className="btn btn-primary" type="submit" disabled={loading}>
                            {loading ? <i className="fas fa-circle-notch fa-spin"></i> : <i className="fas fa-sign-in-alt"></i>}
                            {loading ? ' Signing In...' : ' Sign In'}
                        </button>
                    </form>
                )}

                {view === 'register' && (
                    <form onSubmit={handleRegisterSubmit}>
                        <Input icon="fa-user" type="text" placeholder="Full Name" name="name" value={formData.name} onChange={handleInput} />
                        <Input icon="fa-envelope" type="email" placeholder="Email Address" name="email" value={formData.email} onChange={handleInput} />
                        <Input icon="fa-lock" type="password" placeholder="Password" name="password" value={formData.password} onChange={handleInput} />

                        <button className="btn btn-primary" type="submit" disabled={loading}>
                            {loading ? <i className="fas fa-circle-notch fa-spin"></i> : <i className="fas fa-user-plus"></i>}
                            {loading ? ' Creating...' : ' Create Account'}
                        </button>
                    </form>
                )}

                {view === 'forgotPassword' && (
                    <form onSubmit={handleForgotPasswordSubmit}>
                        <Input icon="fa-envelope" type="email" placeholder="Email Address" name="email" value={formData.email} onChange={handleInput} />
                        <button className="btn btn-primary" type="submit" disabled={loading}>
                            {loading ? <i className="fas fa-circle-notch fa-spin"></i> : <i className="fas fa-paper-plane"></i>}
                            {loading ? ' Sending...' : ' Send Reset Code'}
                        </button>
                        <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.85rem', cursor: 'pointer', color: 'var(--text-muted)' }} onClick={() => { setView('login'); setAlertMsg({ text: '', type: '' }); }}>
                            <i className="fas fa-arrow-left"></i> Back to sign in
                        </div>
                    </form>
                )}

                {view === 'resetPassword' && (
                    <form onSubmit={handleResetPasswordSubmit}>
                        <Input icon="fa-key" type="text" placeholder="6-digit OTP Code" name="otp_code" value={formData.otp_code || ''} onChange={handleInput} />
                        <Input icon="fa-lock" type="password" placeholder="New Password" name="new_password" value={formData.new_password || ''} onChange={handleInput} />
                        <button className="btn btn-primary" type="submit" disabled={loading}>
                            {loading ? <i className="fas fa-circle-notch fa-spin"></i> : <i className="fas fa-check"></i>}
                            {loading ? ' Resetting...' : ' Reset Password'}
                        </button>
                    </form>
                )}

                {(view === 'login' || view === 'register') && (
                    <React.Fragment>
                        <div className="divider">Or continue with</div>
                        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
                            <button className="btn btn-social" style={{ width: '100%' }} type="button" onClick={() => handleSocialLogin('google')} disabled={loading}>
                                <i className="fab fa-google" style={{ color: '#ea4335' }}></i> Google
                            </button>
                        </div>
                        <div className="toggle-view">
                            {view === 'login' ? (
                                <p>Don't have an account? <span onClick={() => { setView('register'); setAlertMsg({ text: '', type: '' }); }}>Sign up</span></p>
                            ) : (
                                <p>Already have an account? <span onClick={() => { setView('login'); setAlertMsg({ text: '', type: '' }); }}>Sign in</span></p>
                            )}
                        </div>

                        <div style={{ marginTop: '1.5rem', textAlign: 'center', fontSize: '0.85rem' }}>
                            <a href="/admin.html" style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: 500 }}>
                                <i className="fas fa-shield-halved"></i> Login as Administrator
                            </a>
                        </div>
                    </React.Fragment>
                )}
            </div>

            {/* OTP Popup Overlay */}
            {showOTP && (
                <OTPPopup
                    email={formData.email}
                    onVerify={handleVerifyOTP}
                    onResend={async () => {
                        try {
                            const res = await fetch('/auth/resend-otp', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ email: formData.email })
                            });
                            const data = await res.json();
                            if (!res.ok) throw new Error(data.detail || 'Resend failed');
                            alert(data.message);
                        } catch (err) {
                            alert(err.message);
                        }
                    }}
                    onCancel={() => setShowOTP(false)}
                />
            )}
        </div>
    );
}

function ChatApp({ token, onLogout, toggleTheme, isDarkMode }) {
    const [user, setUser] = useState(null);
    const [messages, setMessages] = useState([{ role: 'ai', content: 'Hello! I am Bowen AI. How can I assist you with the knowledge base today?' }]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        fetch('/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        })
            .then(res => {
                if (!res.ok) throw new Error('Failed to fetch user');
                return res.json();
            })
            .then(data => setUser(data))
            .catch(err => {
                console.error(err);
                onLogout();
            });
    }, [token, onLogout]);

    useEffect(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages]);

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const newMsg = { role: 'user', content: input };
        setMessages(prev => [...prev, newMsg]);
        setInput('');
        setLoading(true);

        try {
            const res = await fetch('/user/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ question: newMsg.content })
            });

            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.detail || 'Failed to get answer');
            }

            // Append empty message first
            setMessages(prev => [...prev, { role: 'ai', content: '', sources: [] }]);
            
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let fullAnswer = "";
            let sourcesObj = [];

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');
                
                for (let line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const data = JSON.parse(line);
                        if (data.type === 'token') {
                            fullAnswer += data.content || '';
                            setMessages(prev => {
                                const newMessages = [...prev];
                                newMessages[newMessages.length - 1] = { 
                                    ...newMessages[newMessages.length - 1], 
                                    content: fullAnswer,
                                    sources: sourcesObj
                                };
                                return newMessages;
                            });
                        } else if (data.type === 'sources') {
                             sourcesObj = data.data.map(src => ({ filename: src }));
                             setMessages(prev => {
                                const newMessages = [...prev];
                                newMessages[newMessages.length - 1] = { 
                                    ...newMessages[newMessages.length - 1], 
                                    content: fullAnswer,
                                    sources: sourcesObj 
                                };
                                return newMessages;
                            });
                        }
                    } catch (e) {
                         // Some lines might be incomplete chunks, safely ignore
                    }
                }
            }
        } catch (err) {
            setMessages(prev => [...prev, { role: 'ai', content: `Error: ${err.message}` }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="chat-layout">
            <div className="chat-sidebar glass-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                    <h2 className="card-title" style={{ fontSize: '1.2rem', marginBottom: 0 }}>Bowen AI</h2>
                    <button className="theme-toggle" onClick={toggleTheme} type="button" style={{ position: 'static', width: '35px', height: '35px' }}>
                        <i className={`fas ${isDarkMode ? 'fa-sun' : 'fa-moon'}`}></i>
                    </button>
                </div>

                {user ? (
                    <div className="user-profile">
                        <div className="avatar"><i className="fas fa-user"></i></div>
                        <div style={{ overflow: 'hidden' }}>
                            <div style={{ fontWeight: 600, whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{user.full_name || 'User'}</div>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{user.email}</div>
                        </div>
                    </div>
                ) : (
                    <div className="user-profile" style={{ justifyContent: 'center' }}><i className="fas fa-circle-notch fa-spin"></i></div>
                )}

                <div style={{ marginTop: 'auto' }}>
                    <button className="btn btn-social" style={{ width: '100%', justifyContent: 'flex-start', color: '#fca5a5', borderColor: '#fca5a5' }} onClick={onLogout}>
                        <i className="fas fa-sign-out-alt"></i> Sign Out
                    </button>
                </div>
            </div>

            <div className="chat-main glass-card">
                <div className="messages-area">
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`message-wrapper ${msg.role}`}>
                            <div className="message-avatar">
                                <i className={`fas ${msg.role === 'ai' ? 'fa-robot' : 'fa-user'}`}></i>
                            </div>
                            <div className="message-bubble">
                                <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                                {msg.sources && msg.sources.length > 0 && (
                                    <div className="sources-area">
                                        <div style={{ fontSize: '0.75rem', marginTop: '0.5rem', opacity: 0.8 }}><i className="fas fa-book-open"></i> Sources:</div>
                                        {msg.sources.map((src, i) => (
                                            <span key={i} className="source-chip">{src.filename}</span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                    {loading && (
                        <div className="message-wrapper ai">
                            <div className="message-avatar"><i className="fas fa-robot"></i></div>
                            <div className="message-bubble"><i className="fas fa-ellipsis-h fa-fade"></i></div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                <form className="chat-input-area" onSubmit={handleSend}>
                    <input
                        className="input-field"
                        placeholder="Ask Bowen AI anything..."
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        disabled={loading}
                        style={{ flex: 1 }}
                    />
                    <button className="btn btn-primary" style={{ width: '60px', borderRadius: '12px', flexShrink: 0 }} type="submit" disabled={loading || !input.trim()}>
                        <i className="fas fa-paper-plane"></i>
                    </button>
                </form>
            </div>
        </div>
    );
}

function Main() {
    const [token, setToken] = useState(localStorage.getItem('bowen_token'));
    const [isDarkMode, setIsDarkMode] = useState(true);

    const toggleTheme = () => {
        setIsDarkMode(!isDarkMode);
        document.body.classList.toggle('light-mode');
    };

    const handleLogin = (newToken) => {
        localStorage.setItem('bowen_token', newToken);
        setToken(newToken);
    };

    const handleLogout = () => {
        localStorage.removeItem('bowen_token');
        setToken(null);
    };

    if (token) {
        return <ChatApp token={token} onLogout={handleLogout} toggleTheme={toggleTheme} isDarkMode={isDarkMode} />;
    }
    return <AuthApp onLogin={handleLogin} toggleTheme={toggleTheme} isDarkMode={isDarkMode} />;
}

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }
    static getDerivedStateFromError(error) {
        return { hasError: true, error: error };
    }
    componentDidCatch(error, errorInfo) {
        console.error("React Error Boundary caught an error", error, errorInfo);
    }
    render() {
        if (this.state.hasError) {
            return (
                <div style={{ padding: '2rem', color: '#ff5555', background: '#222', zIndex: 9999, position: 'relative' }}>
                    <h2>React Crashed 💥</h2>
                    <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                        {this.state.error && this.state.error.toString()}
                    </pre>
                    <p>Check the console for more details.</p>
                </div>
            );
        }
        return this.props.children;
    }
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
    <ErrorBoundary>
        <Main />
    </ErrorBoundary>
);
