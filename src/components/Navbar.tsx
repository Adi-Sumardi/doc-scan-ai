import { useState, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Upload,
  FileText,
  History,
  Bot,
  Menu,
  X,
  LogIn,
  LogOut,
  User,
  Shield,
  Scale,
  ChevronDown
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const Navbar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [historyDropdownOpen, setHistoryDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setHistoryDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Hide navbar on login/register pages
  if (location.pathname === '/login' || location.pathname === '/register') {
    return null;
  }

  const menuItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/upload', icon: Upload, label: 'Upload' },
    {
      path: '/history',
      icon: History,
      label: 'History',
      hasDropdown: true,
      submenu: [
        { path: '/history', icon: History, label: 'Scan History' },
        { path: '/documents', icon: FileText, label: 'Documents' },
      ]
    },
    { path: '/reconciliation', icon: Scale, label: 'Reconciliation' },
  ];
  
  // Add Admin menu item if user is admin
  const allMenuItems = user?.is_admin 
    ? [...menuItems, { path: '/admin', icon: Shield, label: 'Settings' }]
    : menuItems;
  
  const handleLogout = () => {
    logout();
    navigate('/login');
    closeMobileMenu();
  };

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false);
  };

  return (
    <>
      <nav className="fixed top-0 left-0 right-0 bg-white shadow-lg z-50 border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div className="flex items-center space-x-2 md:space-x-3">
              <div className="w-8 h-8 md:w-10 md:h-10 gradient-bg rounded-lg flex items-center justify-center">
                <Bot className="w-4 h-4 md:w-6 md:h-6 text-white" />
              </div>
              <div>
                <h1 className="text-lg md:text-xl font-bold text-gray-800">AI DocScan</h1>
                <p className="text-xs text-gray-500 hidden sm:block">Document Scanner</p>
              </div>
            </div>

            {/* Desktop Navigation Menu */}
            <div className="hidden lg:flex items-center space-x-1">
              {allMenuItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                const isDropdownItemActive = item.submenu?.some(sub => sub.path === location.pathname);

                if (item.hasDropdown) {
                  return (
                    <div key={item.path} className="relative" ref={dropdownRef}>
                      <button
                        onClick={() => setHistoryDropdownOpen(!historyDropdownOpen)}
                        className={`flex items-center space-x-2 px-3 xl:px-4 py-2 rounded-lg transition-all duration-200 ${
                          isActive || isDropdownItemActive
                            ? 'bg-blue-50 text-blue-600 shadow-sm'
                            : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                        }`}
                      >
                        <Icon className={`w-4 h-4 xl:w-5 xl:h-5 ${isActive || isDropdownItemActive ? 'text-blue-600' : 'text-gray-500'}`} />
                        <span className="font-medium text-sm xl:text-base">{item.label}</span>
                        <ChevronDown className={`w-4 h-4 transition-transform ${historyDropdownOpen ? 'rotate-180' : ''}`} />
                      </button>

                      {historyDropdownOpen && (
                        <div className="absolute top-full left-0 mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                          {item.submenu?.map((subItem) => {
                            const SubIcon = subItem.icon;
                            const isSubActive = location.pathname === subItem.path;
                            return (
                              <Link
                                key={subItem.path}
                                to={subItem.path}
                                onClick={() => setHistoryDropdownOpen(false)}
                                className={`flex items-center space-x-2 px-4 py-2 transition-colors ${
                                  isSubActive
                                    ? 'bg-blue-50 text-blue-600'
                                    : 'text-gray-700 hover:bg-gray-100'
                                }`}
                              >
                                <SubIcon className={`w-4 h-4 ${isSubActive ? 'text-blue-600' : 'text-gray-500'}`} />
                                <span className="text-sm font-medium">{subItem.label}</span>
                              </Link>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                }

                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center space-x-2 px-3 xl:px-4 py-2 rounded-lg transition-all duration-200 ${
                      isActive
                        ? 'bg-blue-50 text-blue-600 shadow-sm'
                        : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                    }`}
                  >
                    <Icon className={`w-4 h-4 xl:w-5 xl:h-5 ${isActive ? 'text-blue-600' : 'text-gray-500'}`} />
                    <span className="font-medium text-sm xl:text-base">{item.label}</span>
                  </Link>
                );
              })}
            </div>

            {/* Mobile & Tablet Navigation Icons */}
            <div className="flex lg:hidden items-center space-x-1">
              {allMenuItems.filter(item => !item.hasDropdown).map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;

                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center p-2 rounded-lg transition-all duration-200 ${
                      isActive
                        ? 'bg-blue-50 text-blue-600 shadow-sm'
                        : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                    }`}
                    title={item.label}
                  >
                    <Icon className={`w-5 h-5 ${isActive ? 'text-blue-600' : 'text-gray-500'}`} />
                  </Link>
                );
              })}
            </div>

            {/* Auth Section & Mobile Menu Button */}
            <div className="flex items-center space-x-2 md:space-x-3">
              {/* User Info & Auth Buttons */}
              {isAuthenticated ? (
                <div className="hidden md:flex items-center space-x-3">
                  <div className="flex items-center space-x-2 px-3 py-1.5 bg-gray-100 rounded-lg">
                    <User className="w-4 h-4 text-gray-600" />
                    <span className="text-sm font-medium text-gray-700">{user?.username}</span>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="flex items-center space-x-2 px-3 py-1.5 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                    <span className="text-sm font-medium">Logout</span>
                  </button>
                </div>
              ) : (
                <div className="hidden md:flex items-center space-x-2">
                  <Link
                    to="/login"
                    className="flex items-center space-x-2 px-3 py-1.5 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <LogIn className="w-4 h-4" />
                    <span className="text-sm font-medium">Login</span>
                  </Link>
                </div>
              )}
              
              {/* Status Indicator */}
              <div className="hidden sm:flex items-center space-x-2 text-green-600">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-xs md:text-sm font-medium hidden lg:block">System Online</span>
                <span className="text-xs md:text-sm font-medium lg:hidden">Online</span>
              </div>

              {/* Mobile Menu Button */}
              <button
                onClick={toggleMobileMenu}
                className="lg:hidden p-2 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
                aria-label="Toggle mobile menu"
              >
                {isMobileMenuOpen ? (
                  <X className="w-5 h-5" />
                ) : (
                  <Menu className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Menu Dropdown */}
        {isMobileMenuOpen && (
          <div className="lg:hidden bg-white border-t border-gray-200 shadow-lg">
            <div className="px-4 py-2 space-y-1">
              {menuItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                const isDropdownItemActive = item.submenu?.some(sub => sub.path === location.pathname);

                if (item.hasDropdown) {
                  return (
                    <div key={item.path}>
                      <button
                        onClick={() => setHistoryDropdownOpen(!historyDropdownOpen)}
                        className={`w-full flex items-center justify-between space-x-3 px-3 py-3 rounded-lg transition-all duration-200 ${
                          isActive || isDropdownItemActive
                            ? 'bg-blue-50 text-blue-600 shadow-sm'
                            : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <Icon className={`w-5 h-5 ${isActive || isDropdownItemActive ? 'text-blue-600' : 'text-gray-500'}`} />
                          <span className="font-medium">{item.label}</span>
                        </div>
                        <ChevronDown className={`w-4 h-4 transition-transform ${historyDropdownOpen ? 'rotate-180' : ''}`} />
                      </button>

                      {historyDropdownOpen && (
                        <div className="ml-8 mt-1 space-y-1">
                          {item.submenu?.map((subItem) => {
                            const SubIcon = subItem.icon;
                            const isSubActive = location.pathname === subItem.path;
                            return (
                              <Link
                                key={subItem.path}
                                to={subItem.path}
                                onClick={closeMobileMenu}
                                className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-all duration-200 ${
                                  isSubActive
                                    ? 'bg-blue-50 text-blue-600'
                                    : 'text-gray-700 hover:bg-gray-100'
                                }`}
                              >
                                <SubIcon className={`w-4 h-4 ${isSubActive ? 'text-blue-600' : 'text-gray-500'}`} />
                                <span className="text-sm font-medium">{subItem.label}</span>
                              </Link>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                }

                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={closeMobileMenu}
                    className={`flex items-center space-x-3 px-3 py-3 rounded-lg transition-all duration-200 ${
                      isActive
                        ? 'bg-blue-50 text-blue-600 shadow-sm'
                        : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                    }`}
                  >
                    <Icon className={`w-5 h-5 ${isActive ? 'text-blue-600' : 'text-gray-500'}`} />
                    <span className="font-medium">{item.label}</span>
                  </Link>
                );
              })}
              
              {/* Auth Section in Mobile Menu */}
              <div className="border-t border-gray-100 mt-2 pt-2 md:hidden">
                {isAuthenticated ? (
                  <>
                    <div className="flex items-center space-x-3 px-3 py-2 text-gray-700">
                      <User className="w-5 h-5 text-gray-500" />
                      <span className="font-medium">{user?.username}</span>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center space-x-3 px-3 py-3 rounded-lg text-red-600 hover:bg-red-50 transition-all"
                    >
                      <LogOut className="w-5 h-5" />
                      <span className="font-medium">Logout</span>
                    </button>
                  </>
                ) : (
                  <Link
                    to="/login"
                    onClick={closeMobileMenu}
                    className="flex items-center space-x-3 px-3 py-3 rounded-lg text-gray-700 hover:bg-gray-100 transition-all"
                  >
                    <LogIn className="w-5 h-5 text-gray-500" />
                    <span className="font-medium">Login</span>
                  </Link>
                )}
              </div>
              
              {/* Mobile Status in Menu */}
              <div className="flex items-center space-x-3 px-3 py-3 text-green-600 border-t border-gray-100 mt-2 pt-3">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm font-medium">System Online</span>
              </div>
            </div>
          </div>
        )}
      </nav>

      {/* Overlay for mobile menu */}
      {isMobileMenuOpen && (
        <div 
          className="lg:hidden fixed inset-0 bg-black bg-opacity-25 z-40"
          onClick={closeMobileMenu}
        />
      )}
    </>
  );
};

export default Navbar;