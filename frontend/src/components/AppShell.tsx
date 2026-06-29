import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { navGroups } from '@/lib/page-config'

const titles: Record<string, string> = {
  '/dashboard': 'FARS 看板',
  '/sources': 'Idea Pool',
  '/insights': 'Hypothesis',
  '/research': 'Research Runs',
  '/research/methodology': 'Plan',
  '/research-queue': '研究队列',
  '/research/context': '研究上下文',
  '/research/readiness': '就绪检查',
  '/research/rounds': '研究轮次',
  '/sessions': '研究运行',
  '/research/audit': '过程审计',
  '/evidence': 'Review',
  '/artifacts': 'Outputs',
  '/benchmarks': 'Benchmark',
  '/reviews': '审查事件',
  '/decisions': 'Decision',
  '/knowledge/experiences': 'Lesson',
  '/capabilities': '能力目录',
  '/status': '系统状态',
}

export function AppShell() {
  const location = useLocation()
  const title = titles[location.pathname] ?? 'AutoResearch'

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
            <div className="brand-mark">AR</div>
            <div>
              <div className="brand-name">AutoResearch</div>
            <div className="brand-subtitle">AI 科研控制台</div>
            </div>
        </div>
        <nav className="nav-groups" aria-label="主导航">
          {navGroups.map((group) => (
            <div className="nav-group" key={group.title}>
              <div className="nav-title">{group.title}</div>
              {group.items.map((item) => {
                const Icon = item.icon
                const isAliasActive = item.activePaths?.some((path) => location.pathname === path)
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) => `nav-item ${isActive || isAliasActive ? 'active' : ''}`}
                  >
                    <Icon size={17} />
                    <span>{item.label}</span>
                  </NavLink>
                )
              })}
            </div>
          ))}
        </nav>
      </aside>
      <main className="main">
        <header className="header">
          <h1>{title}</h1>
          <div className="header-note">AI Runtime 通过 REST/OpenAPI 发送事实；人类只观察研究运行、产出和质量门。</div>
        </header>
        <section className="content">
          <Outlet />
        </section>
      </main>
    </div>
  )
}
