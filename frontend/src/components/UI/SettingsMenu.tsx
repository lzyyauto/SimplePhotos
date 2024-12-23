import ReactDOM from 'react-dom/client'
import { Menu } from '@headlessui/react'
import { useSettingsStore } from '../../stores/settingsStore'
import { api } from '../../services/api'
import { useState } from 'react'
import { GlobalLoading } from '../Loading/GlobalLoading'

export const SettingsMenu = () => {
  const { title, desktopColumns, mobileColumns, setTitle, setDesktopColumns, setMobileColumns } = useSettingsStore()
  const [isLoading, setIsLoading] = useState(false)
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  const handleRefreshLibrary = async () => {
    if (isLoading) return; // 防止重复点击
    
    setIsLoading(true)
    setIsMenuOpen(false)

    // 添加加载动画到 body
    const loadingElement = document.createElement('div')
    loadingElement.id = 'global-loading'
    document.body.appendChild(loadingElement)
    
    // 渲染加载组件
    const root = ReactDOM.createRoot(loadingElement)
    root.render(<GlobalLoading />)

    try {
      const response = await api.post('/scan')
      if (response.status === 'success') {
        const message = `扫描完成！\n处理了 ${response.data.folders_processed} 个文件夹\n${response.data.images_processed} 张图片`
        const notification = document.createElement('div')
        notification.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-6 py-4 rounded-lg shadow-lg transform transition-all duration-500 ease-in-out'
        notification.textContent = message
        document.body.appendChild(notification)
        
        setTimeout(() => {
          notification.style.opacity = '0'
          setTimeout(() => document.body.removeChild(notification), 500)
        }, 3000)
      }
    } catch (error) {
      console.error('刷新库失败:', error)
      const errorNotification = document.createElement('div')
      errorNotification.className = 'fixed bottom-4 right-4 bg-red-500 text-white px-6 py-4 rounded-lg shadow-lg'
      errorNotification.textContent = '刷新库失败，请稍后重试'
      document.body.appendChild(errorNotification)
      
      setTimeout(() => {
        errorNotification.style.opacity = '0'
        setTimeout(() => document.body.removeChild(errorNotification), 500)
      }, 3000)
    } finally {
      setIsLoading(false)
      // 移除加载动画
      const loadingElement = document.getElementById('global-loading')
      if (loadingElement) {
        loadingElement.style.opacity = '0'
        setTimeout(() => document.body.removeChild(loadingElement), 500)
      }
    }
  }

  return (
    <Menu as="div" className="relative">
      <Menu.Button 
        className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
        onClick={() => setIsMenuOpen(true)}
      >
        {isLoading ? (
          <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        ) : (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          </svg>
        )}
      </Menu.Button>

      {isMenuOpen && (
        <Menu.Items 
          static
          className="absolute right-0 mt-2 w-64 origin-top-right bg-white dark:bg-gray-800 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
        >
          <div className="px-4 py-3">
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">标题</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">桌面端列数</label>
              <input
                type="number"
                value={desktopColumns}
                onChange={(e) => setDesktopColumns(Number(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">移动端列数</label>
              <input
                type="number"
                value={mobileColumns}
                onChange={(e) => setMobileColumns(Number(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600"
              />
            </div>

            <Menu.Item>
              {({ active }) => (
                <button
                  onClick={handleRefreshLibrary}
                  disabled={isLoading}
                  className={`${
                    active ? 'bg-gray-100 dark:bg-gray-700' : ''
                  } w-full flex items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-200 rounded-md ${
                    isLoading ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                >
                  {isLoading ? (
                    <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  )}
                  {isLoading ? '刷新中...' : '刷新图库'}
                </button>
              )}
            </Menu.Item>
          </div>
        </Menu.Items>
      )}
    </Menu>
  )
} 