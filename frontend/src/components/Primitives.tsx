import type { ReactNode } from 'react'

type SelectOption = string | { value: string; label: string }

export function Panel({ children, title }: { children: ReactNode; title?: string }) {
  return (
    <section className="panel">
      {title ? <h2>{title}</h2> : null}
      {children}
    </section>
  )
}

export function Button({
  children,
  type = 'button',
  disabled,
  onClick,
}: {
  children: ReactNode
  type?: 'button' | 'submit'
  disabled?: boolean
  onClick?: () => void
}) {
  return (
    <button className="button" type={type} disabled={disabled} onClick={onClick}>
      {children}
    </button>
  )
}

export function TextInput({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
    </label>
  )
}

export function SelectInput({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  options: SelectOption[]
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => {
          const value = typeof option === 'string' ? option : option.value
          const label = typeof option === 'string' ? option : option.label
          return (
          <option key={value} value={value}>
            {label}
          </option>
          )
        })}
      </select>
    </label>
  )
}

export function TextArea({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
}) {
  return (
    <label className="field field-wide">
      <span>{label}</span>
      <textarea value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
    </label>
  )
}

export function StatusBadge({ status }: { status?: string }) {
  const labels: Record<string, string> = {
    planned: '已计划',
    queued: '排队中',
    claimed: '已领取',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    rejected: '已拒绝',
    superseded: '已替代',
    blocked: '阻塞',
    degraded: '降级',
    ready: '就绪',
    pass: '通过',
    warn: '警告',
    archived: '已归档',
  }
  return <span className={`status status-${status || 'neutral'}`}>{status ? labels[status] ?? status : '无状态'}</span>
}

export function WarningList({ warnings }: { warnings?: string[] }) {
  if (!warnings?.length) return null
  return (
    <div className="warning-list">
      {warnings.map((warning) => (
        <div key={warning}>{warning}</div>
      ))}
    </div>
  )
}

export function ErrorMessage({ message }: { message?: string }) {
  if (!message) return null
  return <div className="error-message">{message}</div>
}

export function RecordList({
  items,
  empty = '暂无记录',
}: {
  items?: Array<Record<string, unknown>>
  empty?: string
}) {
  if (!items?.length) {
    return <div className="empty">{empty}</div>
  }
  return (
    <div className="record-list">
      {items.map((item) => (
        <article className="record-row" key={String(item.id)}>
          <div>
            <div className="record-title">{String(item.title || item.name || item.id)}</div>
            <div className="record-meta">{String(item.id)}</div>
          </div>
          <StatusBadge status={typeof item.status === 'string' ? item.status : undefined} />
        </article>
      ))}
    </div>
  )
}
