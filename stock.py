import configparser
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
from loguru import logger
from bs4 import BeautifulSoup
import traceback
import json
import os
import telebot


logger.add('log.log', format="{time} {level} {message}", level="INFO")


def get_settings(key, value):
    config = configparser.ConfigParser()
    config.read('settings.ini', encoding='utf-8')
    return config.get(key, value)


bot = telebot.TeleBot(token=get_settings('TELEGRAM', 'token'))


def notification_data(type_, data=None):
    if type_ == 'save':
        with open('data.json', 'w', encoding='utf-8') as file:
            json.dump(data, file)
    elif type_ == 'load':
        if 'data.json' in os.listdir():
            return json.loads(open('data.json', 'r', encoding='utf-8').read())
        else:
            return []


def used_dates(type_, data=None):
    if type_ == 'save':
        with open('used_dates.json', 'w', encoding='utf-8') as file:
            json.dump(data, file)
    elif type_ == 'load':
        if 'data.json' in os.listdir():
            return json.loads(open('used_dates.json', 'r', encoding='utf-8').read())
        else:
            return {}


def get_browser():
    options = webdriver.ChromeOptions()
    options.add_argument(rf'--user-data-dir={os.path.abspath(os.curdir)}\Profile')
    options.add_argument(r'--profile-directory=Profile')
    options.add_argument('--start-maximized')
    if get_settings('BROWSER', 'headless') == '1':
        options.add_argument('--headless')
    browser = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),
                               options=options)
    return browser


def auth():
    browser = get_browser()
    browser.get('https://seller.wildberries.ru/')
    input('Авторизуйтесь в аккаунт вручную. После авторизации нажмите Enter.')
    time.sleep(3)
    browser.quit()


def check_dates(browser):
    browser.get('https://seller.wildberries.ru/supplies-management/warehouses-limits')
    time.sleep(int(get_settings('SETTINGS', 'sleep_page_load')))
    stock_name = 'Все'
    try:
        stock_value = browser.find_element(By.CLASS_NAME, 'Selected-item__text__zgIl7kP11W').text.strip().lower()
    except Exception as error:
        return [False, f'Ошибка при определении выбранного склада: {error}']
    if stock_value != stock_name.lower():
        try:
            browser.find_element(By.CLASS_NAME, 'Multi-select-input__DuC5x-zT8h').click()
            time.sleep(2)
            stock_input = browser.find_element(By.ID, 'warehouses-multi-input')
            stock_input.send_keys(stock_name)
        except Exception as error:
            return [False, f'Ошибка при поиске окошка ввода названия склада: {error}']
        time.sleep(3)
        try:
            stock_buttons = browser.find_elements(By.CLASS_NAME, 'Dropdown-item__euclVxI-Iy')
            if len(stock_buttons) == 1 and stock_buttons[0].text.strip() == 'Склад не найден':
                return [False, 'Не удается найти склад: Склад не найден']
            else:
                for button in stock_buttons:
                    if button.text.strip().lower() == stock_name.lower():
                        button.click()
                        break
                else:
                    return [False, 'Не удается найти склад: нет подходящего названия']
        except Exception as error:
            return [False, f'Ошибка при выборе склада: {error}']

    try:
        browser.find_element(By.CLASS_NAME, 'Date-input__icon-button__KwAudgjWF-').click()
        time.sleep(2)
    except Exception as error:
        return [False, f'Ошибка при клике на колонку с датами: {error}']
    buttons_all = browser.find_elements(By.CLASS_NAME, 'Day__2Ov02eOoWM')
    buttons = []
    for button in buttons_all:
        if 'Day--disabled__oB6mtnh2Q1' not in button.get_attribute('class')\
                and 'Day--is-empty__l16SbL12eq' not in button.get_attribute('class'):
            buttons.append(button)
    #try:
    #    browser.find_element(By.CLASS_NAME, 'Input-search-icons__arrow__t3UDtiORyz')
    #    browser.find_element(By.CLASS_NAME, 'Date-input__icon-button__KwAudgjWF-').click()
    #    time.sleep(int(get_settings('SETTINGS', 'sleep_click_date_button')))
    #except Exception as error:
    #    return [False, f'Ошибка при клике на колонку с датами: {error}']
    data = {}
    need_stocks = [value.split('-')[0].strip() for value in get_settings('SETTINGS', 'stock_name').split(',')]
    for i in range(0, len(buttons), 7):
        if i != 0:
            try:
                buttons_all = browser.find_elements(By.CLASS_NAME, 'Day__2Ov02eOoWM')
                buttons_ = []
                for button in buttons_all:
                    if 'Day--disabled__oB6mtnh2Q1' not in button.get_attribute('class') \
                            and 'Day--is-empty__l16SbL12eq' not in button.get_attribute('class'):
                        buttons_.append(button)
                browser.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", buttons_[i])
                time.sleep(2)
                buttons_[i].click()
                time.sleep(int(get_settings('SETTINGS', 'sleep_click_date_button')))
                browser.find_element(By.CLASS_NAME, 'Date-input__icon-button__KwAudgjWF-').click()
                time.sleep(int(get_settings('SETTINGS', 'sleep_click_date_button')))
            except Exception as error:
                return [False, f'Ошибка при клике на колонку с датами: {traceback.format_exc()}']
        soup = BeautifulSoup(browser.page_source, 'lxml')
        stocks = soup.find_all('div', {'class': 'Limits-table__warehouse-item__9EKMBScgVB'})
        stocks_values = soup.find_all('div', {'class': 'Limits-table__table-body__kR9Q+dx9Dm'})
        dates = soup.find('div', {'class': 'Limits-table__table-header__ji5l4cCWzI'})
        if dates is not None:
            dates = [
                date.text.strip() for date in
                dates.find_all('div', {'class': 'Limits-table__header-cell__XIbRF-vdt+'})
            ]
        else:
            return [False, 'Не удалось определить даты']
        if len(stocks) == 0 or len(stocks_values) == 0:
            return [False, f'Не удалось найти таблицу со складами на страницу']

        for index_stock in range(len(stocks)):
            stock_name = stocks[index_stock].text.strip()
            if stock_name.lower() in [value.lower() for value in need_stocks]:
                stock_info = stocks_values[index_stock]
                if not stock_name in data:
                    data[stock_name] = {}
                    data[stock_name]['Короба'] = {}
                    data[stock_name]['Монопаллеты'] = {}
                    data[stock_name]['Суперсейф'] = {}
                for i in range(3):
                    stock_type = stock_info.find_all('div', {'class': 'Limits-table__table-row__F01IcFLtBl'})[i]
                    stocks_info = stock_type.find_all('div', {
                        'class': 'Coefficient-table-cell__coefficient-text__fgaDS4ltFS'})
                    for index in range(len(stocks_info)):
                        if i == 0:
                            data[stock_name]['Короба'][dates[index]] = stocks_info[index].text.strip()
                        elif i == 1:
                            data[stock_name]['Монопаллеты'][dates[index]] = stocks_info[index].text.strip()
                        elif i == 2:
                            data[stock_name]['Суперсейф'][dates[index]] = stocks_info[index].text.strip()
    return [True, data]


def create_task(browser, stock_name, stock_date, stock_type):
    browser.get('https://seller.wildberries.ru/supplies-management/all-supplies')
    time.sleep(int(get_settings('SETTINGS', 'sleep_page_load')))
    soup = BeautifulSoup(browser.page_source, 'lxml')
    elements = soup.find_all('div', {'class': 'Table-row-view__crZy+qOLgK'})
    for element in elements:
        if element.find_all('div', {'class': 'Table-row-view__cell__1DEklZnmHI'})[6].text.strip() == stock_name:
            order_id = element.find_all('div', {'class': 'Table-row-view__cell__1DEklZnmHI'})[0].text.strip()
            if order_id != '-' and order_id.isdigit():
                browser.get(f'https://seller.wildberries.ru/supplies-management/all-supplies/supply-detail/uploaded-goods?preorderId={order_id}&supplyId')
                time.sleep(int(get_settings('SETTINGS', 'sleep_page_load')))
                browser.find_element(By.CLASS_NAME, 'Button-link__WZSHBUPfv6.Button-link--button__W4VnJkJpUo.Button-link--interface__nW6u8-ozS9.Button-link--button-big__Dzu380O-7D').click()
                time.sleep(int(get_settings('SETTINGS', 'sleep_page_load')))
                calendar_elements = browser.find_elements(By.CLASS_NAME, 'Calendar-cell__Piudjaz8vL')
                break
    else:
        return [False]
    for element in calendar_elements:
        if 'Calendar-cell--is-disabled__ltdegRF7EA' not in element.get_attribute('class'):
            try:
                date = element.find_element(By.CLASS_NAME, 'Calendar-cell__date-container__rSABI6hXYm').text.strip()
                date = date.split()[0].strip()
                if len(date) == 1:
                    date = '0' + date
            except:
                continue
            if date == stock_date.split('.')[0]:
                kf = element.find_element(By.CLASS_NAME, 'Coefficient-table-cell__coefficient-text__fgaDS4ltFS').text.strip()
                if kf == 'Бесплатно':
                    try:
                        element.find_element(By.CLASS_NAME, 'Button-link__WZSHBUPfv6').click()
                        time.sleep(3)
                    except Exception as error:
                        logger.error(traceback.format_exc())
                        return [False, traceback.format_exc()]
                    if stock_type == 'Монопаллеты':
                        try:
                            browser.find_element(By.ID, 'palette-amount').send_keys(get_settings('SETTINGS', 'pallet_count'))
                            time.sleep(3)
                            browser.find_element(By.CLASS_NAME, 'Button-link__WZSHBUPfv6.Button-link--button__W4VnJkJpUo.Button-link--main__zCUKvVftlU.Button-link--button-big__Dzu380O-7D').click()
                            time.sleep(3)
                        except Exception as error:
                            logger.error(traceback.format_exc())
                            return [False, traceback.format_exc()]
                    try:
                        button = browser.find_element(By.CLASS_NAME, 'Calendar-plan-modal__modal-block--transfer__6wK61yJ6V0')
                        button = button.find_element(By.CLASS_NAME, 'Button-link__WZSHBUPfv6')
                        button.click()
                        time.sleep(5)
                        browser.find_element(By.CLASS_NAME, 'Breadcrumbs-layout__71DdE90jNU').screenshot('screen.png')
                        return [True, order_id, browser.current_url]
                    except Exception as error:
                        logger.error(traceback.format_exc())
                        return [False, traceback.format_exc()]
    else:
        browser.save_screenshot('error.png')
        return [False, 'Не удалось найти свободную дату для поставки', 'error.png']


def send_notif(stock_name, stock_type, stock_date, type_, browser=None):
    need_stocks = [value.strip() for value in get_settings('SETTINGS', 'stock_name').split(',')]
    stocks = {}
    for stock in need_stocks:
        stocks[stock.split('-')[0].strip().lower()] = [st.strip().lower() for st in stock.split('-')[1].split(':')]
    if stock_type.lower() in stocks[stock_name.lower()]:
        if type_ == 'Бесплатно':
            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.add(
                telebot.types.InlineKeyboardButton(
                    text='Перейти', url=get_settings('TELEGRAM', 'button_link'),
                    callback_data='None'
                )
            )
            for user in [int(value.strip()) for value in get_settings('TELEGRAM', 'users').split(',')]:
                try:
                    bot.send_message(
                        user,
                        text=f'🔔 Склад: <b>{stock_name}</b>\nДата поставки: <b>{stock_date}</b>\nТип поставки: <b>{stock_type}</b>\n'
                             f'Коэффициент: <b>{type_}</b>',
                        parse_mode='html',
                        reply_markup=keyboard
                    )
                except Exception as error:
                    logger.error(f'Ошибка при отправке сообщения пользователю {user}: {error}')
            supply_data = used_dates('load')
            if get_settings('SETTINGS', 'add_supply') == '1' and (stock_name not in supply_data or stock_date not in supply_data[stock_name]):
                result = create_task(browser, stock_name, stock_date, stock_type)
                for user in [int(value.strip()) for value in get_settings('TELEGRAM', 'users').split(',')]:
                    if result[0]:
                        if stock_name in supply_data:
                            supply_data[stock_name].append(stock_date)
                        else:
                            supply_data[stock_name] = [stock_date]
                        used_dates('save', supply_data)
                        try:
                            keyboard = telebot.types.InlineKeyboardMarkup()
                            keyboard.add(
                                telebot.types.InlineKeyboardButton(
                                    text='Перейти', url=result[2],
                                    callback_data='None'
                                )
                            )
                            bot.send_photo(
                                user,
                                photo=open('screen.png', 'rb'),
                                caption=f'Успешно создал поставку для даты <b>{stock_date}</b>. Склад: <b>{stock_name}</b>',
                                parse_mode='html',
                                reply_markup=keyboard
                            )
                        except Exception as error:
                            logger.error(f'Ошибка при отправке сообщения пользователю {user}: {error}')
                    else:
                        if len(result) == 2:
                            try:
                                bot.send_message(
                                    user,
                                    text=f'Поставка для даты <b>{stock_date}</b> и склада <b>{stock_name}</b> не была создана'
                                         f'\n\nПричина: {result[1]}',
                                    parse_mode='html',
                                    reply_markup=keyboard
                                )
                            except Exception as error:
                                logger.error(f'Ошибка при отправке сообщения пользователю {user}: {error}')
                        elif len(result) == 3:
                            try:
                                bot.send_photo(
                                    user,
                                    photo=open('error.png', 'rb'),
                                    caption=f'Поставка для даты <b>{stock_date}</b> и склада <b>{stock_name}</b> не была создана'
                                            f'\n\nПричина: {result[1]}',
                                    parse_mode='html',
                                    reply_markup=keyboard
                                )
                            except Exception as error:
                                logger.error(f'Ошибка при отправке сообщения пользователю {user}: {error}')


def check():
    browser = get_browser()
    if get_settings('WORKING MODE', 'close_browser') == '1':
        for i in range(int(get_settings('SETTINGS', 'count_check'))):
            data = notification_data('load')
            result = check_dates(browser)
            if result[0] is False:
                logger.error(result[1])
            else:
                logger.info(result[1])
                for stock_name in result[1]:
                    for stock_type in result[1][stock_name]:
                        for stock_date in result[1][stock_name][stock_type]:
                            if result[1][stock_name][stock_type][stock_date] == 'Бесплатно':
                                if [stock_name, stock_type, stock_date] not in data:
                                    send_notif(
                                        stock_name, stock_type, stock_date, result[1][stock_name][stock_type][stock_date],
                                        browser
                                    )
                                data.append([stock_name, stock_type, stock_date])
                                notification_data('save', data)
            time.sleep(int(get_settings('SETTINGS', 'sleep_seconds')))
        browser.quit()
    elif get_settings('WORKING MODE', 'close_browser') == '0':
        while True:
            data = notification_data('load')
            result = check_dates(browser)
            if result[0] is False:
                logger.error(result[1])
            else:
                logger.info(result[1])
                for stock_name in result[1]:
                    for stock_type in result[1][stock_name]:
                        for stock_date in result[1][stock_name][stock_type]:
                            if result[1][stock_name][stock_type][stock_date] == 'Бесплатно':
                                if not [stock_name, stock_type, stock_date] in data:
                                    send_notif(
                                        stock_name, stock_type, stock_date, result[1][stock_name][stock_type][stock_date]
                                    )
                                    data.append([stock_name, stock_type, stock_date])
                                    notification_data('save', data)
                            else:
                                if [stock_name, stock_type, stock_date] in data:
                                    send_notif(
                                        stock_name, stock_type, stock_date, result[1][stock_name][stock_type][stock_date]
                                    )
                                    data.remove([stock_name, stock_type, stock_date])
                                    notification_data('save', data)
            time.sleep(int(get_settings('SETTINGS', 'sleep_seconds')))


def main():
    if get_settings('WORKING MODE', 'mode') == '0':
        auth()
    elif get_settings('WORKING MODE', 'mode') == '1':
        if get_settings('WORKING MODE', 'endless_mode') == '0':
            try:
                check()
            except Exception as error:
                logger.error(f'Ошибка при работе программы: {error}\n\n{traceback.format_exc()}')
        elif get_settings('WORKING MODE', 'endless_mode') == '1':
            while True:
                try:
                    check()
                except Exception as error:
                    logger.error(f'Ошибка при работе программы: {error}\n\n{traceback.format_exc()}')
                logger.info(f"Ухожу на паузу {int(get_settings('SETTINGS', 'sleep_after_browser_close'))} секунд.")
                time.sleep(int(get_settings('SETTINGS', 'sleep_after_browser_close')))


if __name__ == '__main__':
    main()