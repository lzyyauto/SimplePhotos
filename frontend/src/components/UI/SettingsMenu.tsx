import { Menu, Transition } from '@headlessui/react'
import { Fragment, useState } from 'react'
import { useSettingsStore } from '../../stores/settingsStore'
import { useToastStore } from '../../stores/toastStore'
import { api } from '../../services/api'

export const SettingsMenu = () => {
  const { title, desktopColumns, mobileColumns, setTitle, setDesktopColumns, setMobileColumns } = useSettingsStore()
  const { addToast } = useToastStore()
  const [isLoading, setIsLoading] = useState(false)
  const MIN_COLUMNS = 1
  const MAX_COLUMNS = 12

  const handleRefreshLibrary = async () => {
    if (isLoading) return;
    setIsLoading(true)
    addToast('开始扫描图库...', 'info', 2000)

    try {
      const response = await api.post('/scan')
      if (response.status === 'success') {
        const message = `扫描完成！\n处理了 ${response.data.folders_processed} 个文件夹\n${response.data.images_processed} 张图片`
        addToast(message, 'success', 3000)
      }
    } catch (error) {
      console.error('刷新库失败:', error)
      addToast('刷新图库失败，请稍后重试', 'error', 3000)
    } finally {
      setIsLoading(false)
    }
  }

  // 处理数字调整
  const handleAdjustNumber = (
    currentValue: number,
    setter: (value: number) => void,
    increment: boolean
  ) => {
    const newValue = increment ? currentValue + 1 : currentValue - 1
    if (newValue >= MIN_COLUMNS && newValue <= MAX_COLUMNS) {
      setter(newValue)
    }
  }

  // 数字输入组件
  const NumberInput = ({ 
    value, 
    setter, 
    label 
  }: { 
    value: number, 
    setter: (value: number) => void, 
    label: string 
  }) => (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">{label}</label>
      <div className="flex items-center mt-2 p-1 bg-gray-50 dark:bg-gray-900/50 rounded-xl border border-gray-200 dark:border-white/5">
        <button
          onClick={() => handleAdjustNumber(value, setter, false)}
          disabled={value <= MIN_COLUMNS}
          className={`flex items-center justify-center w-8 h-8 bg-white dark:bg-gray-800 rounded-lg transition-colors shadow-sm
            ${value <= MIN_COLUMNS ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer'}`}
          title={value <= MIN_COLUMNS ? "已达到最小值" : undefined}
        >
          -
        </button>
        <div className="flex-1 text-center font-medium text-gray-900 dark:text-gray-100">
          {value}
        </div>
        <button
          onClick={() => handleAdjustNumber(value, setter, true)}
          disabled={value >= MAX_COLUMNS}
          className={`flex items-center justify-center w-8 h-8 bg-white dark:bg-gray-800 rounded-lg transition-colors shadow-sm
            ${value >= MAX_COLUMNS ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer'}`}
          title={value >= MAX_COLUMNS ? "已达到最大值" : undefined}
        >
          +
        </button>
      </div>
    </div>
  )

  return (
    <Menu as="div" className="relative inline-block text-left">
      {() => (
        <>
          <Menu.Button className="p-2 rounded-xl text-gray-500 hover:bg-gray-100/80 dark:text-gray-400 dark:hover:bg-gray-800/80 transition-colors focus:outline-none">
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

          <Transition
            as={Fragment}
            enter="transition ease-out duration-200"
            enterFrom="transform opacity-0 scale-95 translate-y-2"
            enterTo="transform opacity-100 scale-100 translate-y-0"
            leave="transition ease-in duration-150"
            leaveFrom="transform opacity-100 scale-100 translate-y-0"
            leaveTo="transform opacity-0 scale-95 translate-y-2"
          >
            <Menu.Items className="absolute right-0 top-full mt-2 w-72 origin-top-right bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl rounded-2xl shadow-xl ring-1 ring-black/5 dark:ring-white/10 focus:outline-none z-50 p-1">
              <div className="px-5 py-4">
                <div className="mb-5">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">标题</label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="mt-2 block w-full rounded-xl border-gray-200 shadow-sm focus:border-gray-400 focus:ring-0 dark:bg-gray-800 dark:border-gray-700 dark:text-white transition-colors p-2 text-sm"
                    placeholder="请输入相册标题"
                  />
                </div>

                <div className="bg-gray-100 h-[1px] w-full my-4 dark:bg-gray-800"></div>

                <NumberInput 
                  value={desktopColumns} 
                  setter={setDesktopColumns} 
                  label="桌面端列数"
                />

                <NumberInput 
                  value={mobileColumns} 
                  setter={setMobileColumns} 
                  label="移动端列数"
                />

                <div className="bg-gray-100 h-[1px] w-full my-4 dark:bg-gray-800"></div>

                <Menu.Item>
                  {({ active }) => (
                    <button
                      onClick={handleRefreshLibrary}
                      disabled={isLoading}
                      className={`${
                        active ? 'bg-gray-100 dark:bg-gray-800' : ''
                      } w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-800 dark:text-gray-200 rounded-xl transition-colors ${
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
                      {isLoading ? '刷新中...' : '深度扫描图库'}
                    </button>
                  )}
                </Menu.Item>
              </div>
            </Menu.Items>
          </Transition>
        </>
      )}
    </Menu>
  )
}