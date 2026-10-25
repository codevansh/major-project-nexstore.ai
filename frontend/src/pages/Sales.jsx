import { useState, useRef, Fragment } from 'react'
import { PageHeader, ErrorBox, Empty, Loading, Pill, useLoad } from '../ui'
import { api, inr, getStore, setStore } from '../api'

export function POS() {
    const [store, setS] = useState(getStore())
    const [code, setCode] = useState('')
    const [cart, setCart] = useState([])
    const [customer, setCustomer] = useState('')
    const [payment, setPayment] = useState('cash')
    const [discount, setDiscount] = useState(0)
    const [error, setError] = useState('')
    const [receipt, setReceipt] = useState(null)
    const [busy, setBusy] = useState(false)
    const input = useRef(null)
    const { data: customers } = useLoad(() => api.get('/customers', { limit: 100 }), [])

    async function add(e) {
        e.preventDefault()
        const barcode = code.trim()
        if (!barcode) return
        setError(''); setReceipt(null)
        const existing = cart.find((l) => l.barcode === barcode)
        const qty = (existing?.quantity || 0) + 1
        try {
            const r = await api.post('/sales/scan', { barcode, store_id: store, quantity: qty })
            if (!r.inventory.can_purchase) {
                setError(`Only ${r.inventory.available} of "${r.product.name}" in stock at ${store}.`)
            } else {
                setCart((c) => existing
                    ? c.map((l) => (l.barcode === barcode ? { ...l, quantity: qty } : l))
                    : [...c, { barcode, name: r.product.name, price: r.product.selling_price, quantity: 1 }])
                setCode('')
            }
        } catch (err) { setError(err.message) }
        input.current?.focus()
    }

    const bump = (barcode, d) =>
        setCart((c) => c.map((l) => (l.barcode === barcode ? { ...l, quantity: l.quantity + d } : l)).filter((l) => l.quantity > 0))
    const subtotal = cart.reduce((s, l) => s + l.price * l.quantity, 0)
    const total = Math.max(0, subtotal - (Number(discount) || 0))

    async function checkout() {
        setBusy(true); setError('')
        try {
            const sale = await api.post('/sales/checkout', {
                store_id: store, customer_id: customer || null, payment_method: payment,
                discount: Number(discount) || 0,
                items: cart.map((l) => ({ barcode: l.barcode, quantity: l.quantity })),
            })
            setReceipt(sale); setCart([]); setDiscount(0)
        } catch (err) { setError(err.message) }
        setBusy(false)
    }

    return (
        <>
            <PageHeader title="Sales & billing" subtitle="Scan or type a barcode to build a bill.">
                <input className="input" style={{ width: 150 }} aria-label="Store ID" value={store}
                    onChange={(e) => { setS(e.target.value); setStore(e.target.value) }} />
            </PageHeader>
            <div className="pos">
                <div className="card">
                    <form onSubmit={add} style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
                        <input ref={input} autoFocus className="input" placeholder="Scan or enter barcode" value={code} onChange={(e) => setCode(e.target.value)} />
                        <button className="btn primary">Add</button>
                    </form>
                    <ErrorBox>{error}</ErrorBox>
                    {receipt && (
                        <div className="ok">Sale <b>{receipt.invoice_number}</b> completed — {inr(receipt.total)} by {receipt.payment_method}.</div>
                    )}
                    {cart.length === 0 ? <Empty title="Bill is empty" hint="Scan a product to add it." /> : cart.map((l) => (
                        <div key={l.barcode} className="cart-line">
                            <div><b>{l.name}</b><div style={{ color: 'var(--muted)', fontSize: 12 }}>{l.barcode} · {inr(l.price)}</div></div>
                            <div className="qty">
                                <button aria-label={`Decrease ${l.name}`} onClick={() => bump(l.barcode, -1)}>−</button>
                                <span>{l.quantity}</span>
                                <button aria-label={`Increase ${l.name}`} onClick={() => bump(l.barcode, 1)}>+</button>
                            </div>
                            <b>{inr(l.price * l.quantity)}</b>
                        </div>
                    ))}
                </div>
                <div className="card">
                    <h3>Payment</h3>
                    <div className="field"><label>Customer (optional)</label>
                        <select value={customer} onChange={(e) => setCustomer(e.target.value)}>
                            <option value="">Walk-in</option>
                            {(customers || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                        </select></div>
                    <div className="row2">
                        <div className="field"><label>Method</label>
                            <select value={payment} onChange={(e) => setPayment(e.target.value)}>
                                {['cash', 'card', 'upi'].map((m) => <option key={m}>{m}</option>)}
                            </select></div>
                        <div className="field"><label>Discount (₹)</label>
                            <input type="number" min="0" step="any" value={discount} onChange={(e) => setDiscount(e.target.value)} /></div>
                    </div>
                    <div className="totals">
                        <div><span>Subtotal</span><span>{inr(subtotal)}</span></div>
                        <div><span>Discount</span><span>−{inr(Number(discount) || 0)}</span></div>
                        <div className="grand"><span>Total</span><span>{inr(total)}</span></div>
                    </div>
                    <button className="btn primary" style={{ width: '100%', marginTop: 14 }} disabled={!cart.length || busy} onClick={checkout}>
                        {busy ? 'Processing…' : `Charge ${inr(total)}`}
                    </button>
                </div>
            </div>
        </>
    )
}

export function SalesHistory() {
    const [skip, setSkip] = useState(0)
    const { data, error, loading } = useLoad(() => api.get('/sales', { skip, limit: 50 }), [skip])
    const [open, setOpen] = useState(null)
    const rows = data || []
    return (
        <>
            <PageHeader title="Sales history" subtitle="Every completed bill." />
            <ErrorBox>{error}</ErrorBox>
            <div className="card">
                {loading ? <Loading /> : rows.length === 0 ? <Empty title="No sales yet" hint="Complete a bill on the Sales & billing page." /> : (
                    <div className="tbl-wrap"><table>
                        <thead><tr><th>Invoice</th><th>Store</th><th className="r">Items</th><th>Payment</th><th className="r">Total</th><th>Status</th></tr></thead>
                        <tbody>{rows.map((s) => (
                            <Fragment key={s.id}>
                                <tr onClick={() => setOpen(open === s.id ? null : s.id)} style={{ cursor: 'pointer' }}>
                                    <td><b>{s.invoice_number}</b></td><td>{s.store_id}</td><td className="r">{s.items.length}</td>
                                    <td>{s.payment_method}</td><td className="r">{inr(s.total)}</td><td><Pill tone="green">{s.status}</Pill></td>
                                </tr>
                                {open === s.id && (
                                    <tr><td colSpan={6} style={{ background: '#f8f9fd' }}>
                                        {s.items.map((i) => <div key={i.barcode}>{i.quantity} × {i.name} — {inr(i.subtotal)}</div>)}
                                    </td></tr>
                                )}
                            </Fragment>))}</tbody>
                    </table></div>
                )}
                {(skip > 0 || rows.length === 50) && (
                    <div className="actions" style={{ justifyContent: 'flex-end', marginTop: 12 }}>
                        <button className="btn sm" disabled={!skip} onClick={() => setSkip(Math.max(0, skip - 50))}>Previous</button>
                        <button className="btn sm" disabled={rows.length < 50} onClick={() => setSkip(skip + 50)}>Next</button>
                    </div>
                )}
            </div>
        </>
    )
}
