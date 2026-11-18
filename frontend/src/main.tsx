import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { createRoot } from 'react-dom/client'
import './style.css'

const labels = { todo: 'To do', in_progress: 'In progress', done: 'Done' }
type Status = keyof typeof labels
type TaskInput = { title: string; description: string; status: Status }
type Task = TaskInput & { id: number }

const statuses = Object.keys(labels) as Status[]
const emptyTask: TaskInput = { title: '', description: '', status: 'todo' }

async function request<T>(path = '', method = 'GET', data?: TaskInput): Promise<T> {
  const response = await fetch('/api/tasks' + path, {
    method,
    headers: data ? { 'Content-Type': 'application/json' } : undefined,
    body: data ? JSON.stringify(data) : undefined,
  })
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(typeof error?.detail === 'string' ? error.detail : 'The request failed.')
  }
  return response.status === 204 ? undefined as T : response.json()
}

function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [filter, setFilter] = useState<Status | 'all'>('all')
  const [draft, setDraft] = useState<TaskInput>(emptyTask)
  const [editing, setEditing] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadFailed, setLoadFailed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const titleField = useRef<HTMLInputElement>(null)

  async function loadTasks() {
    setLoading(true)
    setError('')
    setLoadFailed(false)
    try {
      setTasks(await request<Task[]>())
    } catch {
      setLoadFailed(true)
      setError('Could not load tasks. Check the connection to the API.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadTasks() }, [])

  function resetForm() {
    setEditing(null)
    setDraft(emptyTask)
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const title = draft.title.trim()
    if (!title) {
      setError('Enter a task name.')
      titleField.current?.focus()
      return
    }
    setBusy(true)
    setError('')
    try {
      const input = { ...draft, title }
      const task = editing === null
        ? await request<Task>('', 'POST', input)
        : await request<Task>('/' + editing, 'PUT', input)
      setTasks(current => editing === null
        ? [task, ...current]
        : current.map(item => item.id === task.id ? task : item))
      if (filter !== 'all' && filter !== task.status) setFilter('all')
      resetForm()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Could not save the task.')
    } finally {
      setBusy(false)
    }
  }

  async function remove(task: Task) {
    if (!window.confirm('Delete task “' + task.title + '”?')) return
    setBusy(true)
    setError('')
    try {
      await request('/' + task.id, 'DELETE')
      setTasks(current => current.filter(item => item.id !== task.id))
      if (editing === task.id) resetForm()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Could not delete the task.')
    } finally {
      setBusy(false)
    }
  }

  const visible = tasks.filter(task => filter === 'all' || task.status === filter)
  const done = tasks.filter(task => task.status === 'done').length

  return (
    <>
      <header className="topbar">
        <div className="brand"><span className="brand-mark" aria-hidden="true">✓</span> Task Manager</div>
      </header>
      <main>
        <div className="overview">
          <div>
            <h1>My tasks</h1>
            <p>Plan your work and track your progress.</p>
          </div>
          <div className="progress">
            <span>Completed <strong>{done} of {tasks.length}</strong></span>
            <progress aria-label="Task completion" value={done} max={tasks.length || 1} />
          </div>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="layout">
          <section className="panel editor" aria-labelledby="form-title">
            <h2 id="form-title">{editing === null ? 'New task' : 'Edit task'}</h2>
            <form onSubmit={save}>
              <fieldset disabled={busy || loading || loadFailed}>
                <label>Task name
                  <input ref={titleField} value={draft.title} onChange={event => setDraft({ ...draft, title: event.target.value })} maxLength={120} required />
                </label>
                <label>Description <span className="optional">(optional)</span>
                  <textarea rows={4} value={draft.description} onChange={event => setDraft({ ...draft, description: event.target.value })} maxLength={1000} />
                </label>
                <label>Task status
                  <select value={draft.status} onChange={event => setDraft({ ...draft, status: event.target.value as Status })}>
                    {statuses.map(status => <option key={status} value={status}>{labels[status]}</option>)}
                  </select>
                </label>
                <div className="form-actions">
                  <button className="primary" type="submit">{editing === null ? 'Add task' : 'Save changes'}</button>
                  {editing !== null && <button type="button" onClick={resetForm}>Cancel</button>}
                </div>
              </fieldset>
            </form>
          </section>
          <section className="panel tasks" aria-labelledby="list-title">
            <div className="list-header">
              <h2 id="list-title">Task list <span className="count">{visible.length}</span></h2>
              <label className="filter">Filter by status
                <select value={filter} onChange={event => setFilter(event.target.value as Status | 'all')}>
                  <option value="all">All statuses</option>
                  {statuses.map(status => <option key={status} value={status}>{labels[status]}</option>)}
                </select>
              </label>
            </div>
            {loading && <p className="empty" role="status">Loading tasks…</p>}
            {loadFailed && <div className="empty"><button onClick={() => void loadTasks()}>Try again</button></div>}
            {!loading && !loadFailed && (visible.length === 0
              ? <p className="empty">{filter === 'all' ? 'Add your first task to get started.' : 'No tasks match this status.'}</p>
              : <ul>{visible.map(task => (
                <li key={task.id}>
                  <article>
                    <div className="task-heading">
                      <h3>{task.title}</h3>
                      <span className={'status ' + task.status}>{labels[task.status]}</span>
                    </div>
                    {task.description && <p className="description">{task.description}</p>}
                    <div className="task-actions">
                      <button disabled={busy} onClick={() => {
                        setEditing(task.id)
                        setDraft({ title: task.title, description: task.description, status: task.status })
                        setError('')
                        titleField.current?.focus()
                      }}>Edit</button>
                      <button className="danger" disabled={busy} onClick={() => void remove(task)}>Delete</button>
                    </div>
                  </article>
                </li>
              ))}</ul>)}
          </section>
        </div>
      </main>
    </>
  )
}

createRoot(document.getElementById('root')!).render(<App />)
