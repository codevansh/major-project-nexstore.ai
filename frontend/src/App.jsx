import { useState } from 'react'
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './Auth'
import * as Ic from './Icons'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import { POS, SalesHistory } from './pages/Sales'
import { Products, Inventory, Customers, Suppliers, Purchases, Expenses } from './pages/Resources'
import Forecast from './pages/Forecast'

const NAV = [
  ['/', 'Dashboard', Ic.Home],
  ['/billing', 'Sales & billing', Ic.Cart],
  ['/sales', 'Sales history', Ic.Receipt],
  ['/products', 'Products', Ic.Tag],
  ['/inventory', 'Inventory', Ic.Box],
  ['/purchases', 'Purchases', Ic.Bag],
  ['/customers', 'Customers', Ic.Users],
  ['/suppliers', 'Suppliers', Ic.Truck],
  ['/expenses', 'Expenses', Ic.Wallet],
  ['/forecast', 'Demand forecast', Ic.Trend],
]

function Shell() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  return (
    <div className="shell">
      <aside className={`side ${open ? 'open' : ''}`}>
        <div className="brand"><div className="logo">NX</div><div><b>NexStore AI</b><small>The next generation of retail</small></div></div>
        <nav className="nav" onClick={() => setOpen(false)}>
          {NAV.map(([to, label, Icon]) => (
            <NavLink key={to} to={to} end={to === '/'}><Icon />{label}</NavLink>
          ))}
        </nav>
        <div className="spacer" />
        <div className="me"><b>{user.name}</b><small>{user.role}</small>
          <button className="btn sm" onClick={logout}>Sign out</button></div>
      </aside>
      <main className="main">
        <button className="btn menu-btn" style={{ marginBottom: 12 }} onClick={() => setOpen(!open)} aria-label="Toggle menu"><Ic.Menu width="18" height="18" /></button>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/billing" element={<POS />} />
          <Route path="/sales" element={<SalesHistory />} />
          <Route path="/products" element={<Products />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/purchases" element={<Purchases />} />
          <Route path="/customers" element={<Customers />} />
          <Route path="/suppliers" element={<Suppliers />} />
          <Route path="/expenses" element={<Expenses />} />
          <Route path="/forecast" element={<Forecast />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  )
}

function Gate() {
  const { user, loading } = useAuth()
  if (loading) return null
  return user ? <Shell /> : <Login />
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Gate />
        </AuthProvider>
    </BrowserRouter>
  )
}
