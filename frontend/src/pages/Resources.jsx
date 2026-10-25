import { useState } from 'react'
import { ResourcePage, Pill, Modal, ErrorBox, Field, PageHeader, useLoad, Loading, Empty } from '../ui'
import { api, inr, getStore, setStore } from '../api'

const stockTone = { in_stock: 'green', low_stock: 'amber', out_of_stock: 'red' }
const stockLabel = { in_stock: 'In stock', low_stock: 'Low stock', out_of_stock: 'Out of stock' }

export function Products() {
    const base = [
        { name: 'name', label: 'Name', required: true, wide: true },
        { name: 'category', label: 'Category', required: true },
        { name: 'brand', label: 'Brand', required: true },
        { name: 'cost_price', label: 'Cost price (₹)', type: 'number', min: 0, required: true },
        { name: 'selling_price', label: 'Selling price (₹)', type: 'number', min: 0, required: true },
        { name: 'description', label: 'Description', type: 'textarea', wide: true, emptyAs: undefined },
        { name: 'attributes', label: 'Attributes (JSON)', type: 'json', wide: true },
    ]
    return (
        <ResourcePage
            title="Products" subtitle="Your catalogue, prices and barcodes." endpoint="/products" noun="product"
            columns={[
                { label: 'Name', render: (r) => <><b>{r.name}</b><div style={{ color: 'var(--muted)', fontSize: 12 }}>{r.brand}</div></> },
                { key: 'sku', label: 'SKU' },
                { key: 'barcode', label: 'Barcode' },
                { key: 'category', label: 'Category' },
                { label: 'Cost', right: true, render: (r) => inr(r.cost_price) },
                { label: 'Price', right: true, render: (r) => inr(r.selling_price) },
                { label: 'Status', render: (r) => <Pill tone={r.status === 'active' ? 'green' : 'gray'}>{r.status}</Pill> },
            ]}
            createFields={[
                base[0],
                { name: 'sku', label: 'SKU', required: true },
                { name: 'barcode', label: 'Barcode (min 4 chars)', required: true },
                ...base.slice(1),
            ]}
            editFields={[...base, { name: 'status', label: 'Status', options: ['active', 'inactive'] }]}
            toForm={(r) => ({ ...r, attributes: JSON.stringify(r.attributes || {}) })}
        />
    )
}

export function Inventory() {
    const [store, setS] = useState(getStore())
    const prods = { endpoint: '/products', label: (p) => `${p.name} (${p.barcode})` }
    const { data: products } = useLoad(() => api.get('/products', { limit: 100 }), [])
    const nameOf = Object.fromEntries((products || []).map((p) => [p.id, p.name]))
    const stockFields = [
        { name: 'available', label: 'Available', type: 'number', min: 0, default: 0 },
        { name: 'reserved', label: 'Reserved', type: 'number', min: 0, default: 0 },
        { name: 'damaged', label: 'Damaged', type: 'number', min: 0, default: 0 },
        { name: 'reorder_level', label: 'Reorder level', type: 'number', min: 0, default: 10 },
        { name: 'reorder_quantity', label: 'Reorder quantity', type: 'number', min: 1, default: 50 },
    ]
    return (
        <ResourcePage
            title="Inventory" subtitle="Stock levels per product and store." endpoint="/inventory" noun="stock record"
            toolbar={
                <input className="input" style={{ width: 150 }} aria-label="Default store ID" value={store}
                    onChange={(e) => { setS(e.target.value); setStore(e.target.value) }} placeholder="Store ID" />
            }
            columns={[
                { label: 'Product', render: (r) => nameOf[r.product_id] || <span style={{ color: 'var(--muted)' }}>{r.product_id}</span> },
                { key: 'store_id', label: 'Store' },
                { key: 'available', label: 'Available', right: true },
                { key: 'reserved', label: 'Reserved', right: true },
                { key: 'damaged', label: 'Damaged', right: true },
                { key: 'reorder_level', label: 'Reorder at', right: true },
                { label: 'Status', render: (r) => <Pill tone={stockTone[r.stock_status]}>{stockLabel[r.stock_status] || r.stock_status}</Pill> },
            ]}
            createFields={[
                { name: 'product_id', label: 'Product', required: true, wide: true, optionsFrom: prods },
                { name: 'store_id', label: 'Store ID', required: true, default: store, wide: true },
                ...stockFields,
            ]}
            editFields={stockFields}
        />
    )
}

export function Customers() {
    const f = [
        { name: 'name', label: 'Name', required: true, wide: true },
        { name: 'phone', label: 'Phone', emptyAs: undefined },
        { name: 'email', label: 'Email', type: 'email', emptyAs: undefined },
    ]
    const segTone = { vip: 'violet', loyal: 'green', regular: 'blue', new: 'gray' }
    return (
        <ResourcePage
            title="Customers" subtitle="Who buys from you, and how much." endpoint="/customers" noun="customer"
            columns={[
                { key: 'name', label: 'Name' },
                { label: 'Contact', render: (r) => r.phone || r.email || '—' },
                { label: 'Segment', render: (r) => <Pill tone={segTone[r.segment] || 'gray'}>{r.segment}</Pill> },
                { key: 'total_orders', label: 'Orders', right: true },
                { label: 'Total spent', right: true, render: (r) => inr(r.total_spent) },
                { label: 'Avg. order', right: true, render: (r) => inr(r.average_order_value) },
            ]}
            createFields={f} editFields={f}
        />
    )
}

export function Suppliers() {
    const f = [
        { name: 'name', label: 'Name', required: true, wide: true },
        { name: 'phone', label: 'Phone (7–20 chars)', emptyAs: undefined },
        { name: 'email', label: 'Email', type: 'email', emptyAs: undefined },
        { name: 'address', label: 'Address', type: 'textarea', wide: true, emptyAs: undefined },
    ]
    return (
        <ResourcePage
            title="Suppliers" subtitle="Vendors you buy stock from." endpoint="/suppliers" noun="supplier" updateMethod="put"
            columns={[
                { key: 'name', label: 'Name' },
                { label: 'Contact', render: (r) => r.phone || r.email || '—' },
                { label: 'Purchases', right: true, render: (r) => r.purchase_summary?.total_purchases ?? 0 },
                { label: 'Value', right: true, render: (r) => inr(r.purchase_summary?.total_purchase_value) },
                { label: 'Status', render: (r) => <Pill tone={r.status === 'active' ? 'green' : 'gray'}>{r.status}</Pill> },
            ]}
            createFields={f} editFields={f}
        />
    )
}

const toLocalInput = (iso) => (iso ? new Date(new Date(iso).getTime() - new Date(iso).getTimezoneOffset() * 60000).toISOString().slice(0, 16) : '')

export function Expenses() {
    const cats = ['rent', 'utilities', 'salaries', 'maintenance', 'marketing', 'transportation', 'other']
    const f = [
        { name: 'category', label: 'Category', options: cats, default: 'other' },
        { name: 'amount', label: 'Amount (₹)', type: 'number', min: 0, required: true },
        { name: 'payment_method', label: 'Payment method', required: true, default: 'cash' },
        { name: 'expense_date', label: 'Date', type: 'datetime-local', required: true, default: toLocalInput(new Date().toISOString()) },
        { name: 'description', label: 'Description', type: 'textarea', wide: true, emptyAs: undefined },
    ]
    return (
        <ResourcePage
            title="Expenses" subtitle="Rent, salaries and everything else you spend." endpoint="/expenses" noun="expense"
            columns={[
                { label: 'Date', render: (r) => new Date(r.expense_date).toLocaleDateString('en-IN') },
                { label: 'Category', render: (r) => <Pill tone="blue">{r.category}</Pill> },
                { key: 'description', label: 'Description' },
                { key: 'payment_method', label: 'Paid by' },
                { label: 'Amount', right: true, render: (r) => inr(r.amount) },
                { label: 'Status', render: (r) => <Pill tone={r.status === 'active' ? 'green' : 'gray'}>{r.status}</Pill> },
            ]}
            createFields={[{ name: 'store_id', label: 'Store ID', required: true, default: getStore(), wide: true }, ...f]}
            editFields={f}
            toForm={(r) => ({ ...r, expense_date: toLocalInput(r.expense_date) })}
        />
    )
}

export function Purchases() {
    const [skip, setSkip] = useState(0)
    const { data, error, loading, reload } = useLoad(() => api.get('/purchases', { skip, limit: 50 }), [skip])
    const { data: suppliers } = useLoad(() => api.get('/suppliers', { limit: 100 }), [])
    const [open, setOpen] = useState(false)
    const nameOf = Object.fromEntries((suppliers || []).map((s) => [s.id, s.name]))
    const rows = data || []
    return (
        <>
            <PageHeader title="Purchases" subtitle="Stock bought from suppliers. Receiving a purchase adds to inventory.">
                <button className="btn primary" onClick={() => setOpen(true)}>New purchase</button>
            </PageHeader>
            <ErrorBox>{error}</ErrorBox>
            <div className="card">
                {loading ? <Loading /> : rows.length === 0 ? <Empty title="No purchases yet" hint="Record a supplier invoice to restock." /> : (
                    <div className="tbl-wrap"><table>
                        <thead><tr><th>Invoice</th><th>Supplier</th><th>Store</th><th className="r">Items</th><th className="r">Total</th><th>Status</th></tr></thead>
                        <tbody>{rows.map((p) => (
                            <tr key={p.id}>
                                <td><b>{p.invoice_number}</b></td><td>{nameOf[p.supplier_id] || p.supplier_id}</td><td>{p.store_id}</td>
                                <td className="r">{p.items?.length ?? 0}</td><td className="r">{inr(p.total)}</td>
                                <td><Pill tone="green">{p.status}</Pill></td>
                            </tr>))}</tbody>
                    </table></div>
                )}
                {(skip > 0 || rows.length === 50) && (
                    <div className="actions" style={{ justifyContent: 'flex-end', marginTop: 12 }}>
                        <button className="btn sm" disabled={!skip} onClick={() => setSkip(Math.max(0, skip - 50))}>Previous</button>
                        <button className="btn sm" disabled={rows.length < 50} onClick={() => setSkip(skip + 50)}>Next</button>
                    </div>
                )}
            </div>
            {open && <PurchaseModal suppliers={suppliers || []} onClose={() => setOpen(false)} onDone={reload} />}
        </>
    )
}

function PurchaseModal({ suppliers, onClose, onDone }) {
    const [head, setHead] = useState({ invoice_number: '', supplier_id: '', store_id: getStore(), discount: 0, tax: 0 })
    const [items, setItems] = useState([{ barcode: '', quantity: 1, unit_cost: '' }])
    const [error, setError] = useState('')
    const [busy, setBusy] = useState(false)
    const setItem = (i, k, v) => setItems((xs) => xs.map((x, j) => (j === i ? { ...x, [k]: v } : x)))
    const subtotal = items.reduce((s, x) => s + (Number(x.quantity) || 0) * (Number(x.unit_cost) || 0), 0)

    async function submit(e) {
        e.preventDefault()
        setBusy(true); setError('')
        try {
            await api.post('/purchases', {
                ...head, discount: Number(head.discount) || 0, tax: Number(head.tax) || 0,
                items: items.map((x) => ({ barcode: x.barcode.trim(), quantity: Number(x.quantity), unit_cost: Number(x.unit_cost) })),
            })
            onDone(); onClose()
        } catch (err) { setError(err.message); setBusy(false) }
    }
    return (
        <Modal title="New purchase" onClose={onClose}>
            <form onSubmit={submit}>
                <ErrorBox>{error}</ErrorBox>
                <div className="row2">
                    <Field label="Invoice number"><input required value={head.invoice_number} onChange={(e) => setHead({ ...head, invoice_number: e.target.value })} /></Field>
                    <Field label="Store ID"><input required value={head.store_id} onChange={(e) => setHead({ ...head, store_id: e.target.value })} /></Field>
                </div>
                <Field label="Supplier">
                    <select required value={head.supplier_id} onChange={(e) => setHead({ ...head, supplier_id: e.target.value })}>
                        <option value="">Select…</option>
                        {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                    </select>
                </Field>
                <Field label="Items">
                    {items.map((x, i) => (
                        <div key={i} style={{ display: 'grid', gridTemplateColumns: '1.4fr .6fr .8fr auto', gap: 6, marginBottom: 6 }}>
                            <input required minLength={4} placeholder="Barcode" value={x.barcode} onChange={(e) => setItem(i, 'barcode', e.target.value)} />
                            <input required type="number" min="1" placeholder="Qty" value={x.quantity} onChange={(e) => setItem(i, 'quantity', e.target.value)} />
                            <input required type="number" min="0" step="any" placeholder="Unit cost" value={x.unit_cost} onChange={(e) => setItem(i, 'unit_cost', e.target.value)} />
                            <button type="button" className="btn sm" aria-label="Remove item" disabled={items.length === 1} onClick={() => setItems(items.filter((_, j) => j !== i))}>✕</button>
                        </div>
                    ))}
                    <button type="button" className="btn sm" style={{ alignSelf: 'flex-start' }} onClick={() => setItems([...items, { barcode: '', quantity: 1, unit_cost: '' }])}>Add item</button>
                </Field>
                <div className="row2">
                    <Field label="Discount (₹)"><input type="number" min="0" step="any" value={head.discount} onChange={(e) => setHead({ ...head, discount: e.target.value })} /></Field>
                    <Field label="Tax (₹)"><input type="number" min="0" step="any" value={head.tax} onChange={(e) => setHead({ ...head, tax: e.target.value })} /></Field>
                </div>
                <p style={{ color: 'var(--muted)' }}>Items subtotal: <b style={{ color: 'var(--ink)' }}>{inr(subtotal)}</b></p>
                <div className="foot">
                    <button type="button" className="btn" onClick={onClose}>Cancel</button>
                    <button className="btn primary" disabled={busy}>{busy ? 'Saving…' : 'Record purchase'}</button>
                </div>
            </form>
        </Modal>
    )
}
