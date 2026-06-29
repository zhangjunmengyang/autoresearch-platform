import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { navGroups } from '@/lib/page-config'

const titles: Record<string, string> = {
  '/dashboard': '自动研究看板',
  '/sources': '想法池',
  '/insights': '假设',
  '/research': '研究运行',
  '/research/methodology': '计划',
  '/research-queue': '研究队列',
  '/research/context': '研究上下文',
  '/research/readiness': '就绪检查',
  '/research/rounds': '研究轮次',
  '/sessions': '研究运行',
  '/research/audit': '过程审计',
  '/evidence': '审查',
  '/artifacts': '成果',
  '/benchmarks': '评测',
  '/reviews': '审查事件',
  '/decisions': '决策',
  '/knowledge/experiences': '经验',
  '/capabilities': '能力目录',
  '/status': '系统状态',
}

export function AppShell() {
  const location = useLocation()
  const title = titles[location.pathname] ?? '自动研究'

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
            <div className="brand-mark">研</div>
            <div>
              <div className="brand-name">自动研究平台</div>
            <div className="brand-subtitle">科研运行控制台</div>
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
          <div className="header-note">智能运行方通过标准接口发送事实；人类只观察研究运行、产出和质量门。</div>
        </header>
        <section className="content">
          <Outlet />
        </section>
      </main>
    </div>
  )
}
