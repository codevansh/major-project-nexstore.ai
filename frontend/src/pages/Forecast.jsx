import { useState } from 'react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'
import { PageHeader, Field, ErrorBox, Pill, useLoad } from '../ui'
import { api } from '../api'

export default function Forecast() {
    const [productId, setProductId] = useState('')
    const [days, setDays] = useState(7)
    const [result, setResult] = useState(null)
    const [error, setError] = useState('')
    const [busy, setBusy] = useState(false)
    const { data: products } = useLoad(() => api.get('/products', { limit: 100 }), [])

    async function run(e) {
        e.preventDefault()
        setBusy(true); setError(''); setResult(null)
        try { setResult(await api.get('/analytics/demand-forecast', { product_id: productId, horizon_days: days })) }
        catch (err) { setError(err.message) }
        setBusy(false)
    }
    const points = (result?.forecasts || []).map((f) => ({ date: f.date.slice(5), qty: Number(f.predicted_quantity.toFixed(1)) }))
    return (
        <>
            <PageHeader title="Demand forecast" subtitle="Expected daily unit sales for a product." />
            <div className="card" style={{ marginBottom: 16 }}>
                <form onSubmit={run} className="row2" style={{ alignItems: 'end' }}>
                    <Field label="Product ID">
                        <input required list="prods" placeholder="Paste or pick a product ID" value={productId} onChange={(e) => setProductId(e.target.value)} />
                        <datalist id="prods">{(products || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</datalist>
                    </Field>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'end' }}>
                        <Field label="Days ahead"><input type="number" min="1" max="30" value={days} onChange={(e) => setDays(e.target.value)} /></Field>
                        <button className="btn primary" style={{ marginBottom: 12 }} disabled={busy}>{busy ? 'Forecasting…' : 'Forecast'}</button>
                    </div>
                </form>
            </div>
            <ErrorBox>{error}</ErrorBox>
            {result && (
                <div className="card">
                    <div className="actions" style={{ marginBottom: 12 }}>
                        <Pill tone="amber">{result.demo_label}</Pill>
                        <span style={{ color: 'var(--muted)' }}>Model: {result.model} · from {result.forecast_origin} · unit: {result.unit}</span>
                    </div>
                    <ResponsiveContainer width="100%" height={300}>
                        <LineChart data={points}>
                            <CartesianGrid stroke="#e6e9f3" vertical={false} /><XAxis dataKey="date" /><YAxis /><Tooltip />
                            <Line type="monotone" dataKey="qty" name="Predicted units" stroke="#2563eb" strokeWidth={2.5} dot />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}
            <p style={{ color: 'var(--muted)' }}>This forecast runs on a synthetic demo dataset, so only product IDs in that dataset will return a result.</p>
        </>
    )
}
