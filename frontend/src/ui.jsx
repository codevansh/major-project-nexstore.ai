/* eslint-disable react-refresh/only-export-components */
import { useEffect, useState, useCallback } from 'react'
import { api } from './api'

export function useLoad(fn, deps = []) {
    const [state, setState] = useState({ data: null, error: '', loading: true })
    const run = useCallback(() => {
        setState((s) => ({ ...s, loading: true, error: '' }))
        fn()
            .then((data) => setState({ data, error: '', loading: false }))
            .catch((e) => setState({ data: null, error: e.message, loading: false }))
        // The dependency array is intentionally supplied by each useLoad caller.
        // eslint-disable-next-line react-hooks/use-memo, react-hooks/exhaustive-deps
    }, deps)
    useEffect(run, [run])
    return { ...state, reload: run }
}

export function PageHeader({ title, subtitle, children }) {
    return (
        <div className="top">
            <div>
                <h1>{title}</h1>
                {subtitle && <p>{subtitle}</p>}
            </div>
            <div className="actions">{children}</div>
        </div>
    )
}

export const Pill = ({ tone = 'gray', children }) => <span className={`pill ${tone}`}>{children}</span>
export const ErrorBox = ({ children }) => (children ? <div className="err" role="alert">{children}</div> : null)

export function Empty({ title, hint }) {
    return (
        <div className="empty">
            <b>{title}</b>
            {hint}
        </div>
    )
}

export function Loading() {
    return (
        <div style={{ display: 'grid', gap: 10, padding: 8 }}>
            {[80, 100, 90].map((w, i) => <div key={i} className="skeleton" style={{ width: `${w}%` }} />)}
        </div>
    )
}

export function Modal({ title, onClose, children }) {
    useEffect(() => {
        const h = (e) => e.key === 'Escape' && onClose()
        window.addEventListener('keydown', h)
        return () => window.removeEventListener('keydown', h)
    }, [onClose])
    return (
        <div className="scrim" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
            <div className="modal" role="dialog" aria-modal="true" aria-label={title}>
                <h2>{title}</h2>
                {children}
            </div>
        </div>
    )
}

export function Field({ label, children }) {
    return (
        <div className="field">
            <label>{label}</label>
            {children}
        </div>
    )
}

export function Stat({ icon: Icon, tone, label, value }) {
    return (
        <div className="card stat">
            <div className={`ico ${tone}`}><Icon /></div>
            <div>
                <small>{label}</small>
                <strong>{value}</strong>
            </div>
        </div>
    )
}

function OptionsSelect({ spec, value, onChange }) {
    const { data } = useLoad(() => api.get(spec.endpoint, { limit: 100 }), [spec.endpoint])
    return (
        <select required={spec.required} value={value ?? ''} onChange={(e) => onChange(e.target.value)}>
            <option value="">Select…</option>
            {(data || []).map((o) => (
                <option key={o.id} value={o.id}>{spec.label(o)}</option>
            ))}
        </select>
    )
}

/** Form modal driven by a field list. Returns parsed values to onSubmit. */
export function FormModal({ title, fields, initial = {}, onSubmit, onClose, submitLabel = 'Save' }) {
    const [vals, setVals] = useState(() => {
        const v = {}
        fields.forEach((f) => (v[f.name] = initial[f.name] ?? f.default ?? ''))
        return v
    })
    const [error, setError] = useState('')
    const [busy, setBusy] = useState(false)
    const set = (k, v) => setVals((s) => ({ ...s, [k]: v }))

    async function submit(e) {
        e.preventDefault()
        setBusy(true)
        setError('')
        const out = {}
        try {
            fields.forEach((f) => {
                let v = vals[f.name]
                if (f.type === 'number') v = v === '' ? undefined : Number(v)
                else if (f.type === 'json') v = v === '' ? {} : JSON.parse(v)
                else if (f.type === 'datetime-local') v = v ? new Date(v).toISOString() : undefined
                else if (v === '') v = f.emptyAs
                if (v !== undefined) out[f.name] = v
            })
            await onSubmit(out)
            onClose()
        } catch (err) {
            setError(err instanceof SyntaxError ? 'Attributes must be valid JSON, e.g. {"size":"1L"}' : err.message)
            setBusy(false)
        }
    }

    return (
        <Modal title={title} onClose={onClose}>
            <form onSubmit={submit}>
                <ErrorBox>{error}</ErrorBox>
                <div className="row2">
                    {fields.map((f) => (
                        <div key={f.name} style={f.wide ? { gridColumn: '1 / -1' } : undefined}>
                            <Field label={f.label}>
                                {f.optionsFrom ? (
                                    <OptionsSelect spec={{ ...f.optionsFrom, required: f.required }} value={vals[f.name]} onChange={(v) => set(f.name, v)} />
                                ) : f.options ? (
                                    <select required={f.required} value={vals[f.name]} onChange={(e) => set(f.name, e.target.value)}>
                                        {f.options.map((o) => <option key={o} value={o}>{o}</option>)}
                                    </select>
                                ) : f.type === 'textarea' || f.type === 'json' ? (
                                    <textarea required={f.required} value={vals[f.name]} onChange={(e) => set(f.name, e.target.value)} />
                                ) : (
                                    <input
                                        type={f.type || 'text'}
                                        step={f.type === 'number' ? 'any' : undefined}
                                        min={f.min}
                                        required={f.required}
                                        value={vals[f.name]}
                                        onChange={(e) => set(f.name, e.target.value)}
                                    />
                                )}
                            </Field>
                        </div>
                    ))}
                </div>
                <div className="foot">
                    <button type="button" className="btn" onClick={onClose}>Cancel</button>
                    <button className="btn primary" disabled={busy}>{busy ? 'Saving…' : submitLabel}</button>
                </div>
            </form>
        </Modal>
    )
}

/** Generic list + create/edit/delete page, used by most resources. */
export function ResourcePage({
    title, subtitle, endpoint, columns, createFields, editFields, updateMethod = 'patch',
    noun, canDelete = true, params = {}, toolbar, toForm = (r) => r,
}) {
    const LIMIT = 50
    const [skip, setSkip] = useState(0)
    const { data, error, loading, reload } = useLoad(
        () => api.get(endpoint, { skip, limit: LIMIT, ...params }),
        [endpoint, skip, JSON.stringify(params)]
    )
    const [modal, setModal] = useState(null)
    const [actionError, setActionError] = useState('')

    async function remove(row) {
        if (!window.confirm(`Delete this ${noun}? This cannot be undone.`)) return
        try {
            await api.del(`${endpoint}/${row.id}`)
            setActionError('')
            reload()
        } catch (e) {
            setActionError(e.message)
        }
    }

    const rows = data || []
    return (
        <>
            <PageHeader title={title} subtitle={subtitle}>
                {toolbar}
                {createFields && <button className="btn primary" onClick={() => setModal({ mode: 'create' })}>Add {noun}</button>}
            </PageHeader>
            <ErrorBox>{error || actionError}</ErrorBox>
            <div className="card">
                {loading ? <Loading /> : rows.length === 0 && !error ? (
                    <Empty title={`No ${noun}s yet`} hint={createFields ? `Add your first ${noun} to get started.` : 'Nothing to show.'} />
                ) : (
                    <div className="tbl-wrap">
                        <table>
                            <thead>
                                <tr>
                                    {columns.map((c) => <th key={c.label} className={c.right ? 'r' : ''}>{c.label}</th>)}
                                    {(editFields || canDelete) && <th />}
                                </tr>
                            </thead>
                            <tbody>
                                {rows.map((r) => (
                                    <tr key={r.id}>
                                        {columns.map((c) => (
                                            <td key={c.label} className={c.right ? 'r' : ''}>{c.render ? c.render(r) : r[c.key] ?? '—'}</td>
                                        ))}
                                        {(editFields || canDelete) && (
                                            <td className="r" style={{ whiteSpace: 'nowrap' }}>
                                                {editFields && <button className="btn sm" onClick={() => setModal({ mode: 'edit', row: r })}>Edit</button>}{' '}
                                                {canDelete && <button className="btn sm danger" onClick={() => remove(r)}>Delete</button>}
                                            </td>
                                        )}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
                {(skip > 0 || rows.length === LIMIT) && (
                    <div className="actions" style={{ justifyContent: 'flex-end', marginTop: 12 }}>
                        <button className="btn sm" disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - LIMIT))}>Previous</button>
                        <button className="btn sm" disabled={rows.length < LIMIT} onClick={() => setSkip(skip + LIMIT)}>Next</button>
                    </div>
                )}
            </div>
            {modal && (
                <FormModal
                    title={modal.mode === 'create' ? `Add ${noun}` : `Edit ${noun}`}
                    fields={modal.mode === 'create' ? createFields : editFields}
                    initial={modal.mode === 'edit' ? toForm(modal.row) : {}}
                    onClose={() => setModal(null)}
                    onSubmit={async (body) => {
                        if (modal.mode === 'create') await api.post(endpoint, body)
                        else await api[updateMethod](`${endpoint}/${modal.row.id}`, body)
                        reload()
                    }}
                />
            )}
        </>
    )
}
