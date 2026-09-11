/**
 * Frontend smoke tests: no fake content on Login, honest nav in Layout,
 * working Pagination control. Rendered with react-dom directly (no extra deps);
 * ESM-only modules are mocked.
 */
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('axios', () => ({
  defaults: { headers: { common: {} } },
  interceptors: { response: { use: jest.fn(() => 1), eject: jest.fn() } },
  get: jest.fn(() => new Promise(() => {})),
  post: jest.fn(() => new Promise(() => {})),
}));

jest.mock('sonner', () => ({
  toast: { success: jest.fn(), error: jest.fn(), warning: jest.fn() },
  Toaster: () => null,
}));

jest.mock('react-router-dom', () => ({
  useNavigate: () => jest.fn(),
  useLocation: () => ({ pathname: '/' }),
  NavLink: ({ children, to }) => <a href={to}>{children}</a>,
  BrowserRouter: ({ children }) => <div>{children}</div>,
  Routes: ({ children }) => <div>{children}</div>,
  Route: () => null,
  Navigate: () => null,
}));

// Radix-based primitives use package-export subpaths CRA5's jest can't resolve;
// mock them with plain elements (their behavior isn't under test here).
jest.mock('../components/ui/dropdown-menu', () => ({
  DropdownMenu: ({ children }) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children }) => <div>{children}</div>,
  DropdownMenuContent: ({ children }) => <div>{children}</div>,
  DropdownMenuItem: ({ children }) => <div>{children}</div>,
  DropdownMenuSeparator: () => null,
}));

jest.mock('../components/ui/avatar', () => ({
  Avatar: ({ children }) => <div>{children}</div>,
  AvatarFallback: ({ children }) => <div>{children}</div>,
}));

jest.mock('../components/ui/label', () => ({
  Label: ({ children, ...p }) => <label {...p}>{children}</label>,
}));

jest.mock('../components/ui/button', () => ({
  Button: ({ children, ...p }) => <button {...p}>{children}</button>,
}));

jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: { name: 'Test Admin', email: 't@block29.com', role: 'SUPER_ADMIN' },
    login: jest.fn(),
    logout: jest.fn(),
    hasRole: () => true,
    loading: false,
  }),
  AuthProvider: ({ children }) => <div>{children}</div>,
}));

function render(element) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => {
    root.render(element);
  });
  return container;
}

describe('LoginPage', () => {
  const LoginPage = require('../pages/LoginPage').default;

  it('renders Block29 branding with the real ecosystem, no fake content', () => {
    const el = render(<LoginPage />);
    const text = el.textContent;

    expect(text).toContain('Block29 Admin');
    expect(text).toContain('AsterPOS');
    expect(text).toContain('Chain29');
    expect(text).toContain('Agent9');

    // Fake/dead content must not return
    expect(text).not.toContain('Demo Credentials');
    expect(text).not.toContain('admin123');
    expect(text).not.toContain('$2.5M');
    expect(text).not.toContain('500+');
    expect(text).not.toContain('Forgot Password');
    expect(text).not.toContain('Remember me');
    expect(text.toLowerCase()).not.toContain('salonbookin');
    expect(el.querySelector('a[href="#"]')).toBeNull();
  });
});

describe('Layout', () => {
  const Layout = require('../components/Layout').default;

  it('shows only real keeper pages in navigation', () => {
    const el = render(<Layout><div>content</div></Layout>);
    const text = el.textContent;

    for (const label of ['Dashboard', 'Merchants', 'VAR Sheet Setup', 'Terminals & Devices',
      'Transactions', 'Reports', 'Users & Roles', 'System Logs']) {
      expect(text).toContain(label);
    }

    // Removed features must not reappear in navigation
    expect(text).not.toContain('Virtual Terminal');
    expect(text).not.toContain('Block29 Gateway');
    expect(text).not.toContain('Affiliates');
    expect(text).not.toContain('Settings');
    expect(text).not.toContain('SALONBOOKIN');
    expect(text).toContain('BLOCK29');
  });
});

describe('Pagination', () => {
  const Pagination = require('../components/Pagination').default;

  it('shows range and pages correctly', () => {
    const el = render(<Pagination page={1} pageSize={50} total={120} onPageChange={() => {}} />);
    expect(el.textContent).toContain('1–50 of 120');
    expect(el.textContent).toContain('1 / 3');
  });

  it('advances pages via Next', () => {
    const onPageChange = jest.fn();
    const el = render(<Pagination page={1} pageSize={50} total={120} onPageChange={onPageChange} />);
    const next = el.querySelector('[data-testid="pagination-next"]');
    const prev = el.querySelector('[data-testid="pagination-prev"]');
    expect(prev.disabled).toBe(true);
    act(() => {
      next.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it('shows a plain record count when everything fits one page', () => {
    const el = render(<Pagination page={1} pageSize={50} total={8} onPageChange={() => {}} />);
    expect(el.textContent).toContain('8 records');
  });
});
