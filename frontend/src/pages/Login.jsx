import { useState } from 'react'
import { useAuth } from '../Auth'
import { ErrorBox, Field } from '../ui'

export default function Login() {
    const { login, register } = useAuth()
    const [mode, setMode] = useState('login')
    const [f, setF] = useState({ name: '', email: '', password: '' })
    const [error, setError] = useState('')
    const [busy, setBusy] = useState(false)
    const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

    async function submit(e) {
        e.preventDefault()
        setBusy(true); setError('')
        try {
            if (mode === 'login') await login(f.email, f.password)
            else await register(f.name, f.email, f.password)
        } catch (err) { setError(err.message); setBusy(false) }
    }
    return (
        <div className="auth">
            <form className="box" onSubmit={submit}>
                <div className="brand" style={{ color: 'var(--ink)', padding: '0 0 18px' }}>
                    <div className="logo">NX</div><div><b>NexStore AI</b><small style={{ color: 'var(--muted)' }}>Retail management</small></div>
                </div>
                <h1>{mode === 'login' ? 'Sign in' : 'Create your account'}</h1>
                <p>{mode === 'login' ? 'Use the email and password you registered with.' : 'Passwords need at least 8 characters.'}</p>
                <ErrorBox>{error}</ErrorBox>
                {mode === 'register' && <Field label="Name"><input required minLength={2} value={f.name} onChange={set('name')} /></Field>}
                <Field label="Email"><input type="email" required autoComplete="email" value={f.email} onChange={set('email')} /></Field>
                <Field label="Password"><input type="password" required minLength={mode === 'register' ? 8 : 1} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={f.password} onChange={set('password')} /></Field>
                <button className="btn primary" style={{ width: '100%' }} disabled={busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}</button>
                <p style={{ marginTop: 16, marginBottom: 0 }}>
                    {mode === 'login' ? 'New here? ' : 'Already registered? '}
                    <button type="button" className="link" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}>
                        {mode === 'login' ? 'Create an account' : 'Sign in'}
                    </button>
                </p>
            </form>
        </div>
    )
}
