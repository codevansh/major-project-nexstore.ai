import { Link } from 'react-router-dom'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'
import { PageHeader, Stat, Loading, Empty, ErrorBox, useLoad } from '../ui'
import { api, inr, num } from '../api'
import { Wallet, Receipt, Box, Alert, Trend } from '../Icons'
import { useAuth } from '../Auth'

const COLORS = ['#2563eb', '#17a673', '#e8912d', '#6d4fe0', '#e5484d', '#8a93b8']

export default function Dashboard() {
    const { user } = useAuth()
    const { data, error, loading } = useLoad(async () => {
        const [overview, sales, top, low, products, customers, inventory] = await Promise.all([
            api.get('/analytics/overview'), api.get('/analytics/sales'), api.get('/analytics/top-products', { limit: 5 }),
            api.get('/analytics/low-stock'), api.get('/analytics/products'), api.get('/analytics/customers'),
            api.get('/analytics/inventory'),
        ])
        // Finance needs a login and may fail independently; don't break the whole page.
        const finance = await api.get('/analytics/finance').catch(() => null)
        return { overview, sales, top, low, products, customers, inventory, finance }
    })

    const hour = new Date().getHours()
    const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
    const first = user?.name?.split(' ')[0] || ''

    if (loading) return <><PageHeader title={`${greeting}, ${first}`} /><div className="card"><Loading /></div></>
    if (error) return <><PageHeader title="Dashboard" /><ErrorBox>{error}</ErrorBox></>

    const { overview, sales, top, low, products, customers, inventory, finance } = data
    const stock = [
        { name: 'Available', value: inventory.total_available },
        { name: 'Reserved', value: inventory.total_reserved },
        { name: 'Damaged', value: inventory.total_damaged },
    ].filter((x) => x.value > 0)
    const cats = (products.categories || []).map((c) => ({ name: c.category || 'Uncategorised', value: c.product_count }))
    const segs = (customers.segments || []).map((s) => ({ name: s.segment || 'unknown', value: s.customer_count }))
    const topBars = top.map((t) => ({ name: t.product_name, sold: t.quantity_sold }))

    return (
        <>
            <PageHeader title={`${greeting}, ${first}`} subtitle="Here is how your store is doing." />
            <div className="grid stats">
                <Stat icon={Wallet} tone="green" label="Total sales" value={inr(sales.total_sales)} />
                <Stat icon={Receipt} tone="blue" label="Orders" value={num(sales.total_orders)} />
                <Stat icon={Trend} tone="violet" label={finance ? 'Net profit' : 'Avg. order value'} value={inr(finance ? finance.net_profit : sales.average_order_value)} />
                <Stat icon={Box} tone="amber" label="Units in stock" value={num(overview.inventory.total_available)} />
                <Stat icon={Alert} tone="red" label="Low-stock items" value={num(low.length)} />
            </div>

            <div className="grid two">
                <div className="card">
                    <h3>Top selling products</h3>
                    {topBars.length === 0 ? <Empty title="No sales yet" hint="Top sellers appear after your first bill." /> : (
                        <ResponsiveContainer width="100%" height={260}>
                            <BarChart data={topBars} layout="vertical" margin={{ left: 20 }}>
                                <CartesianGrid horizontal={false} stroke="#e6e9f3" />
                                <XAxis type="number" allowDecimals={false} /><YAxis type="category" dataKey="name" width={130} tick={{ fontSize: 12 }} />
                                <Tooltip /><Bar dataKey="sold" name="Units sold" fill="#2563eb" radius={[0, 6, 6, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    )}
                </div>
                <div className="card">
                    <h3>Products by category</h3>
                    <Donut data={cats} centre={num(products.total_products)} sub="products" />
                </div>
            </div>

            <div className="grid three">
                <div className="card"><h3>Inventory status</h3><Donut data={stock} centre={num(inventory.total_inventory_items)} sub="records" /></div>
                <div className="card"><h3>Customer segments</h3><Donut data={segs} centre={num(customers.total_customers)} sub="customers" /></div>
                <div className="card">
                    <h3>Needs restocking</h3>
                    {low.length === 0 ? <Empty title="All stocked up" hint="Nothing is below its reorder level." /> : (
                        <table><tbody>
                            {low.slice(0, 6).map((l, i) => (
                                <tr key={i}><td>{l.product_name}</td><td className="r"><b style={{ color: 'var(--red)' }}>{l.available}</b> / {l.reorder_level}</td></tr>
                            ))}
                        </tbody></table>
                    )}
                    <p style={{ margin: '12px 0 0' }}><Link className="link" to="/inventory">View inventory</Link></p>
                </div>
            </div>

            {finance && (
                <div className="card">
                    <h3>Profit & loss</h3>
                    <div className="grid stats" style={{ marginBottom: 0 }}>
                        {[['Revenue', finance.total_revenue], ['Cost of goods sold', finance.cost_of_goods_sold], ['Purchases', finance.total_purchases], ['Expenses', finance.total_expenses], ['Gross profit', finance.gross_profit], ['Net profit', finance.net_profit]].map(([k, v]) => (
                            <div key={k}><small style={{ color: 'var(--muted)' }}>{k}</small><div style={{ fontSize: 20, fontWeight: 700, color: v < 0 ? 'var(--red)' : undefined }}>{inr(v)}</div></div>
                        ))}
                    </div>
                </div>
            )}
        </>
    )
}

function Donut({ data, centre, sub }) {
    if (!data.length) return <Empty title="No data yet" />
    return (
        <div style={{ position: 'relative' }}>
            <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                    <Pie data={data} dataKey="value" innerRadius={55} outerRadius={85} paddingAngle={2}>
                        {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip />
                </PieChart>
            </ResponsiveContainer>
            <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', pointerEvents: 'none', textAlign: 'center' }}>
                <div><b style={{ fontSize: 20 }}>{centre}</b><div style={{ color: 'var(--muted)', fontSize: 12 }}>{sub}</div></div>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 14px', justifyContent: 'center' }}>
                {data.map((d, i) => (
                    <span key={d.name} style={{ fontSize: 12.5 }}><i style={{ display: 'inline-block', width: 9, height: 9, borderRadius: 3, background: COLORS[i % COLORS.length], marginRight: 5 }} />{d.name} ({d.value})</span>
                ))}
            </div>
        </div>
    )
}
