/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { api, getToken, setToken } from './api'

const Ctx = createContext(null)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(!!getToken())

    const logout = useCallback(() => {
        setToken(null)
        setUser(null)
    }, [])

    useEffect(() => {
        if (getToken()) {
            api.get('/auth/me').then(setUser).catch(() => setToken(null)).finally(() => setLoading(false))
        }
        window.addEventListener('nx-logout', logout)
        return () => window.removeEventListener('nx-logout', logout)
    }, [logout])

    const login = async (email, password) => {
        const { access_token } = await api.login(email, password)
        setToken(access_token)
        setUser(await api.get('/auth/me'))
    }

    const register = async (name, email, password) => {
        await api.post('/auth/register', { name, email, password })
        await login(email, password)
    }

    return <Ctx.Provider value={{ user, loading, login, register, logout }}>{children}</Ctx.Provider>
}
