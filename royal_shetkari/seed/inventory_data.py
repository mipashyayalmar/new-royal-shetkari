"""
Sample stock items, suppliers and recipes for Royal Shetkari.

SAMPLE DATA: cost prices are rough Pune wholesale prices (INR per kg / litre /
piece) for the demo. Supplier names, contacts and addresses are fictional;
supplier GSTINs are left blank on purpose (no business registration is
invented). Phone numbers use the fictional 90000 0xxxx range and emails use
the reserved example.com domain.
"""

# (key, name, contact person, phone, email, area)
SUPPLIERS = [
    ("meat", "Sahyadri Fresh Meats (Sample)", "Imran Shaikh", "+91 90000 01001", "orders@sahyadri-meats.example.com", "Kondhwa, Pune"),
    ("poultry", "Godavari Poultry Farm (Sample)", "Santosh Jadhav", "+91 90000 01002", "sales@godavari-poultry.example.com", "Hadapsar, Pune"),
    ("fish", "Konkan Coast Seafood (Sample)", "Ramesh Tandel", "+91 90000 01003", "fresh@konkan-seafood.example.com", "Ganesh Peth, Pune"),
    ("dairy", "Krishna Valley Dairy (Sample)", "Pallavi Kulkarni", "+91 90000 01004", "supply@krishna-dairy.example.com", "Karad Road, Satara"),
    ("veg", "Shivneri Vegetable Traders (Sample)", "Dattatray More", "+91 90000 01005", "veg@shivneri-traders.example.com", "Market Yard, Pune"),
    ("grocery", "Anand Wholesale Grocers (Sample)", "Mahesh Shah", "+91 90000 01006", "orders@anand-grocers.example.com", "Bhavani Peth, Pune"),
    ("spice", "Kolhapur Masala Bhandar (Sample)", "Sunita Patil", "+91 90000 01007", "masala@kolhapur-bhandar.example.com", "Shivaji Peth, Kolhapur"),
    ("oil", "Deccan Edible Oils (Sample)", "Vikas Deshmukh", "+91 90000 01008", "sales@deccan-oils.example.com", "Bhosari MIDC, Pune"),
    ("bev", "Sahyadri Beverages & Ice Cream (Sample)", "Neha Joshi", "+91 90000 01009", "trade@sahyadri-bev.example.com", "Chakan, Pune"),
    ("bakery", "Bharat Bakery & Farsan (Sample)", "Asif Bagwan", "+91 90000 01010", "bakery@bharat-farsan.example.com", "Camp, Pune"),
    ("fruit", "Ratnagiri Fruit Company (Sample)", "Prakash Sawant", "+91 90000 01011", "fruit@ratnagiri-fruits.example.com", "Gultekdi, Pune"),
]

# (name, category, unit, cost per unit, supplier key, low-stock threshold, reorder qty)
INGREDIENTS = [
    # Meat, poultry, eggs
    ("Chicken (Curry Cut)", "Meat & Poultry", "kg", 220, "poultry", 8, 20),
    ("Boneless Chicken", "Meat & Poultry", "kg", 320, "poultry", 6, 15),
    ("Chicken Drumsticks & Wings", "Meat & Poultry", "kg", 260, "poultry", 4, 10),
    ("Chicken Kheema", "Meat & Poultry", "kg", 300, "poultry", 2, 5),
    ("Mutton (Curry Cut)", "Meat & Poultry", "kg", 780, "meat", 6, 15),
    ("Mutton Kheema", "Meat & Poultry", "kg", 720, "meat", 2, 6),
    ("Mutton Paya", "Meat & Poultry", "kg", 300, "meat", 1, 3),
    ("Eggs", "Meat & Poultry", "pcs", 7, "poultry", 60, 180),
    # Seafood
    ("Surmai (Kingfish)", "Seafood", "kg", 900, "fish", 3, 8),
    ("Pomfret", "Seafood", "kg", 1000, "fish", 3, 8),
    ("Bombil (Bombay Duck)", "Seafood", "kg", 400, "fish", 2, 5),
    ("Prawns", "Seafood", "kg", 650, "fish", 3, 8),
    ("Crab", "Seafood", "kg", 600, "fish", 2, 4),
    ("Tisrya (Clams)", "Seafood", "kg", 300, "fish", 1, 4),
    ("Rawas (Indian Salmon)", "Seafood", "kg", 850, "fish", 2, 5),
    ("Bangda (Mackerel)", "Seafood", "kg", 280, "fish", 2, 5),
    ("Fish Fillet (Basa)", "Seafood", "kg", 380, "fish", 3, 8),
    # Dairy
    ("Paneer", "Dairy", "kg", 340, "dairy", 5, 12),
    ("Milk", "Dairy", "l", 60, "dairy", 15, 40),
    ("Curd", "Dairy", "kg", 80, "dairy", 6, 15),
    ("Butter", "Dairy", "kg", 520, "dairy", 3, 8),
    ("Ghee", "Dairy", "kg", 620, "dairy", 3, 6),
    ("Fresh Cream", "Dairy", "l", 220, "dairy", 3, 6),
    ("Cheese", "Dairy", "kg", 480, "dairy", 2, 5),
    ("Khoya", "Dairy", "kg", 380, "dairy", 2, 4),
    ("Chakka (Hung Curd)", "Dairy", "kg", 160, "dairy", 2, 5),
    # Vegetables and fruit
    ("Onion", "Vegetables", "kg", 32, "veg", 25, 60),
    ("Tomato", "Vegetables", "kg", 36, "veg", 15, 40),
    ("Potato", "Vegetables", "kg", 28, "veg", 15, 40),
    ("Green Chilli", "Vegetables", "kg", 60, "veg", 2, 5),
    ("Ginger", "Vegetables", "kg", 120, "veg", 2, 5),
    ("Garlic", "Vegetables", "kg", 160, "veg", 3, 6),
    ("Coriander Leaves", "Vegetables", "kg", 80, "veg", 2, 5),
    ("Capsicum", "Vegetables", "kg", 70, "veg", 4, 10),
    ("Cauliflower", "Vegetables", "kg", 40, "veg", 4, 10),
    ("Brinjal", "Vegetables", "kg", 40, "veg", 3, 8),
    ("Okra (Bhindi)", "Vegetables", "kg", 50, "veg", 3, 6),
    ("Spinach", "Vegetables", "kg", 40, "veg", 3, 6),
    ("Fenugreek Leaves (Methi)", "Vegetables", "kg", 60, "veg", 1, 3),
    ("Green Peas", "Vegetables", "kg", 90, "veg", 4, 10),
    ("Mushroom", "Vegetables", "kg", 220, "veg", 2, 5),
    ("Sweet Corn", "Vegetables", "kg", 90, "veg", 2, 5),
    ("Mixed Vegetables", "Vegetables", "kg", 60, "veg", 6, 15),
    ("Cabbage & Carrot", "Vegetables", "kg", 35, "veg", 4, 10),
    ("Fresh Coconut", "Vegetables", "pcs", 35, "veg", 15, 40),
    ("Lemon", "Vegetables", "pcs", 4, "veg", 60, 200),
    ("Colocasia Leaves", "Vegetables", "pcs", 3, "veg", 20, 60),
    ("Mango Pulp (Alphonso)", "Fruit", "kg", 160, "fruit", 4, 10),
    ("Watermelon", "Fruit", "kg", 25, "fruit", 6, 15),
    ("Mosambi (Sweet Lime)", "Fruit", "kg", 60, "fruit", 6, 15),
    ("Sugarcane", "Fruit", "kg", 8, "fruit", 15, 40),
    # Dry store
    ("Basmati Rice", "Dry Store", "kg", 110, "grocery", 20, 50),
    ("Kolam Rice", "Dry Store", "kg", 55, "grocery", 10, 25),
    ("Wheat Flour (Atta)", "Dry Store", "kg", 38, "grocery", 15, 40),
    ("Maida", "Dry Store", "kg", 40, "grocery", 10, 25),
    ("Jowar Flour", "Dry Store", "kg", 45, "grocery", 6, 15),
    ("Bajra Flour", "Dry Store", "kg", 42, "grocery", 4, 10),
    ("Besan (Gram Flour)", "Dry Store", "kg", 85, "grocery", 6, 15),
    ("Rice Flour", "Dry Store", "kg", 50, "grocery", 3, 8),
    ("Poha", "Dry Store", "kg", 55, "grocery", 4, 10),
    ("Sabudana", "Dry Store", "kg", 90, "grocery", 4, 10),
    ("Rava (Semolina)", "Dry Store", "kg", 45, "grocery", 3, 8),
    ("Toor Dal", "Dry Store", "kg", 140, "grocery", 6, 15),
    ("Urad Dal (Whole)", "Dry Store", "kg", 130, "grocery", 3, 8),
    ("Moong Dal", "Dry Store", "kg", 120, "grocery", 3, 8),
    ("Chana Dal", "Dry Store", "kg", 95, "grocery", 3, 8),
    ("Kabuli Chana", "Dry Store", "kg", 110, "grocery", 3, 8),
    ("Matki (Moth Beans)", "Dry Store", "kg", 120, "grocery", 4, 10),
    ("Peanuts", "Dry Store", "kg", 130, "grocery", 3, 8),
    ("Cashew Nuts", "Dry Store", "kg", 850, "grocery", 2, 4),
    ("Sugar", "Dry Store", "kg", 44, "grocery", 15, 40),
    ("Jaggery", "Dry Store", "kg", 60, "grocery", 3, 8),
    ("Hakka Noodles", "Dry Store", "kg", 140, "grocery", 3, 8),
    ("Papad", "Dry Store", "pcs", 3, "grocery", 50, 150),
    ("Pav", "Bakery", "pcs", 4, "bakery", 60, 200),
    ("Burger Buns", "Bakery", "pcs", 8, "bakery", 15, 40),
    ("Sandwich Bread", "Bakery", "pcs", 3, "bakery", 30, 80),
    ("Farsan & Sev", "Bakery", "kg", 180, "bakery", 3, 8),
    ("Puri & Chutney Kit", "Bakery", "pcs", 2, "bakery", 60, 200),
    # Oil, spices, sauces
    ("Sunflower Oil", "Oil & Spices", "l", 150, "oil", 20, 45),
    ("Goda Masala", "Oil & Spices", "kg", 450, "spice", 1, 3),
    ("Kolhapuri Masala", "Oil & Spices", "kg", 520, "spice", 1, 3),
    ("Malvani Masala", "Oil & Spices", "kg", 500, "spice", 1, 3),
    ("Garam Masala", "Oil & Spices", "kg", 650, "spice", 1, 2),
    ("Red Chilli Powder", "Oil & Spices", "kg", 320, "spice", 2, 4),
    ("Turmeric Powder", "Oil & Spices", "kg", 220, "spice", 1, 2),
    ("Biryani Masala", "Oil & Spices", "kg", 600, "spice", 1, 2),
    ("Saffron", "Oil & Spices", "g", 300, "spice", 5, 10),
    ("Kokum", "Oil & Spices", "kg", 400, "spice", 1, 2),
    ("Soy & Chilli Sauces", "Oil & Spices", "l", 120, "grocery", 2, 5),
    # Beverages
    ("Tea Leaves", "Beverages", "kg", 420, "grocery", 1, 3),
    ("Filter Coffee Powder", "Beverages", "kg", 700, "grocery", 1, 2),
    ("Soft Drink 300 ml", "Beverages", "pcs", 22, "bev", 24, 96),
    ("Mineral Water 1 L", "Beverages", "pcs", 12, "bev", 24, 96),
    ("Soda 300 ml", "Beverages", "pcs", 12, "bev", 24, 72),
    ("Vanilla Ice Cream", "Beverages", "l", 260, "bev", 4, 10),
    ("Rose Syrup", "Beverages", "l", 180, "bev", 1, 3),
]

G, ML, PCS = "g", "ml", "pcs"


def _has(name, *words):
    n = name.lower()
    return any(w in n for w in words)


def recipe_for(dish):
    """[(ingredient name, quantity, unit)] for one portion of the dish."""
    name, cat = dish["name"], dish["category"]
    n = name.lower()
    lines = []

    def add(ing, qty, unit=G):
        lines.append((ing, qty, unit))

    # ---- Beverages ----
    if cat == "Beverages":
        table = {
            "Masala Chai": [("Tea Leaves", 4), ("Milk", 100, ML), ("Sugar", 12), ("Ginger", 3)],
            "Cutting Chai": [("Tea Leaves", 3), ("Milk", 60, ML), ("Sugar", 10)],
            "Filter Coffee": [("Filter Coffee Powder", 10), ("Milk", 120, ML), ("Sugar", 10)],
            "Cold Coffee": [("Filter Coffee Powder", 10), ("Milk", 200, ML), ("Sugar", 20), ("Vanilla Ice Cream", 60, ML)],
            "Sol Kadhi": [("Kokum", 10), ("Fresh Coconut", 0.25, PCS), ("Garlic", 3)],
            "Masala Taak": [("Curd", 120), ("Ginger", 3), ("Coriander Leaves", 3)],
            "Sweet Lassi": [("Curd", 200), ("Sugar", 25)],
            "Mango Lassi": [("Curd", 150), ("Mango Pulp (Alphonso)", 80), ("Sugar", 15)],
            "Kokum Sharbat": [("Kokum", 15), ("Sugar", 30)],
            "Fresh Lime Soda": [("Lemon", 1, PCS), ("Soda 300 ml", 1, PCS), ("Sugar", 15)],
            "Fresh Lime Water": [("Lemon", 1, PCS), ("Sugar", 15)],
            "Jaljeera": [("Lemon", 1, PCS), ("Garam Masala", 2), ("Sugar", 10)],
            "Sugarcane Juice": [("Sugarcane", 600), ("Lemon", 0.5, PCS), ("Ginger", 3)],
            "Watermelon Juice": [("Watermelon", 450), ("Sugar", 10)],
            "Mosambi Juice": [("Mosambi (Sweet Lime)", 500)],
            "Piyush": [("Chakka (Hung Curd)", 100), ("Milk", 100, ML), ("Sugar", 30), ("Saffron", 0.05)],
            "Kesar Masala Doodh": [("Milk", 220, ML), ("Sugar", 20), ("Saffron", 0.05), ("Cashew Nuts", 5)],
            "Mineral Water (1 L)": [("Mineral Water 1 L", 1, PCS)],
            "Soft Drink (300 ml)": [("Soft Drink 300 ml", 1, PCS)],
            "Aam Panna": [("Mango Pulp (Alphonso)", 60), ("Sugar", 20)],
        }
        return [(i[0], i[1], i[2] if len(i) > 2 else G) for i in table[name]]

    # ---- Desserts ----
    if cat == "Desserts":
        table = {
            "Gulab Jamun (2 pcs)": [("Khoya", 50), ("Sugar", 40), ("Sunflower Oil", 15, ML)],
            "Shrikhand": [("Chakka (Hung Curd)", 120), ("Sugar", 35), ("Saffron", 0.05)],
            "Amrakhand": [("Chakka (Hung Curd)", 110), ("Mango Pulp (Alphonso)", 40), ("Sugar", 30)],
            "Basundi": [("Milk", 300, ML), ("Sugar", 30), ("Cashew Nuts", 5)],
            "Ukadiche Modak (2 pcs)": [("Rice Flour", 60), ("Fresh Coconut", 0.25, PCS), ("Jaggery", 40), ("Ghee", 10)],
            "Rasmalai (2 pcs)": [("Milk", 250, ML), ("Sugar", 35), ("Saffron", 0.05)],
            "Kheer": [("Milk", 220, ML), ("Basmati Rice", 25), ("Sugar", 30), ("Cashew Nuts", 5)],
            "Gajar Halwa": [("Cabbage & Carrot", 180), ("Milk", 100, ML), ("Khoya", 30), ("Sugar", 35), ("Ghee", 15)],
            "Moong Dal Halwa": [("Moong Dal", 60), ("Ghee", 35), ("Sugar", 40), ("Cashew Nuts", 5)],
            "Jalebi": [("Maida", 60), ("Sugar", 60), ("Sunflower Oil", 20, ML), ("Saffron", 0.02)],
            "Jalebi with Rabdi": [("Maida", 50), ("Sugar", 70), ("Milk", 200, ML), ("Sunflower Oil", 20, ML)],
            "Malai Kulfi": [("Milk", 180, ML), ("Sugar", 25), ("Khoya", 20)],
            "Pista Kulfi": [("Milk", 180, ML), ("Sugar", 25), ("Cashew Nuts", 10)],
            "Royal Falooda": [("Milk", 200, ML), ("Rose Syrup", 20, ML), ("Vanilla Ice Cream", 60, ML), ("Sugar", 15)],
            "Vanilla Ice Cream": [("Vanilla Ice Cream", 120, ML)],
            "Brownie with Ice Cream": [("Maida", 50), ("Butter", 30), ("Sugar", 40), ("Vanilla Ice Cream", 60, ML), ("Eggs", 1, PCS)],
            "Rava Sheera": [("Rava (Semolina)", 60), ("Ghee", 20), ("Sugar", 40), ("Cashew Nuts", 5)],
            "Kaju Katli (4 pcs)": [("Cashew Nuts", 60), ("Sugar", 30)],
            "Malpua": [("Maida", 60), ("Milk", 150, ML), ("Sugar", 40), ("Ghee", 20)],
            "Phirni": [("Milk", 200, ML), ("Basmati Rice", 25), ("Sugar", 30)],
        }
        return [(i[0], i[1], i[2] if len(i) > 2 else G) for i in table[name]]

    # ---- Breads ----
    if cat == "Roti and Breads":
        if _has(n, "bhakri"):
            add("Jowar Flour" if "jowar" in n else "Bajra Flour", 90)
        elif _has(n, "naan", "kulcha"):
            add("Maida", 90)
            add("Curd", 15)
            if _has(n, "butter"):
                add("Butter", 10)
            if _has(n, "garlic"):
                add("Garlic", 8)
            if _has(n, "cheese"):
                add("Cheese", 40)
            if _has(n, "kashmiri"):
                add("Cashew Nuts", 15)
            if _has(n, "kulcha"):
                add("Potato", 60)
        elif _has(n, "basket"):
            add("Maida", 200); add("Wheat Flour (Atta)", 160); add("Butter", 25)
        elif _has(n, "puri"):
            add("Wheat Flour (Atta)", 70); add("Sunflower Oil", 25, ML)
        else:
            add("Wheat Flour (Atta)", 70 if "paratha" not in n else 110)
            if _has(n, "butter", "laccha", "paratha", "poli"):
                add("Butter" if "butter" in n else "Ghee", 10)
            if _has(n, "aloo"):
                add("Potato", 100)
            if _has(n, "paneer"):
                add("Paneer", 70)
            if _has(n, "missi"):
                add("Besan (Gram Flour)", 30)
        return lines

    # ---- Biryani and rice ----
    if cat == "Biryani and Rice":
        if _has(n, "fried rice"):
            add("Basmati Rice", 120); add("Cabbage & Carrot", 50); add("Soy & Chilli Sauces", 15, ML); add("Sunflower Oil", 20, ML)
            if "chicken" in n:
                add("Boneless Chicken", 100)
            if "egg" in n or "chicken" in n:
                add("Eggs", 1 if "chicken" in n else 2, PCS)
            return lines
        if _has(n, "biryani"):
            add("Basmati Rice", 160); add("Onion", 60); add("Biryani Masala", 8); add("Ghee", 15); add("Curd", 40); add("Saffron", 0.03)
            if "mutton kheema" in n:
                add("Mutton Kheema", 180)
            elif "mutton" in n:
                add("Mutton (Curry Cut)", 230)
            elif "chicken" in n:
                add("Boneless Chicken" if "tikka" in n else "Chicken (Curry Cut)", 220)
                if "special" in n:
                    add("Eggs", 1, PCS); add("Kolhapuri Masala", 6)
            elif "egg" in n:
                add("Eggs", 2, PCS)
            elif "prawn" in n:
                add("Prawns", 180)
            elif "paneer" in n:
                add("Paneer", 130)
            else:
                add("Mixed Vegetables", 150)
            return lines
        rice = "Basmati Rice"
        add(rice, 130 if "steamed" not in n else 150)
        if _has(n, "jeera"):
            add("Ghee", 10)
        if _has(n, "veg pulao"):
            add("Mixed Vegetables", 80); add("Ghee", 10)
        if _has(n, "peas"):
            add("Green Peas", 60); add("Ghee", 10)
        if _has(n, "kashmiri"):
            add("Cashew Nuts", 15); add("Saffron", 0.03); add("Ghee", 10)
        if _has(n, "curd"):
            add("Curd", 150)
        if _has(n, "khichdi"):
            lines[0] = ("Kolam Rice", 90, G); add("Moong Dal", 60); add("Ghee", 15); add("Papad", 1, PCS)
        return lines

    # ---- Snacks and fast food ----
    if cat == "Snacks and Fast Food":
        table = {
            "Vada Pav": [("Potato", 90), ("Besan (Gram Flour)", 25), ("Pav", 1, PCS), ("Sunflower Oil", 20, ML), ("Garlic", 3)],
            "Samosa (2 pcs)": [("Maida", 60), ("Potato", 120), ("Green Peas", 15), ("Sunflower Oil", 30, ML)],
            "Samosa Pav": [("Maida", 30), ("Potato", 60), ("Pav", 1, PCS), ("Sunflower Oil", 15, ML)],
            "Pav Bhaji": [("Mixed Vegetables", 120), ("Potato", 80), ("Tomato", 60), ("Butter", 25), ("Pav", 2, PCS)],
            "Cheese Pav Bhaji": [("Mixed Vegetables", 120), ("Potato", 80), ("Tomato", 60), ("Butter", 25), ("Cheese", 30), ("Pav", 2, PCS)],
            "Dabeli": [("Potato", 80), ("Peanuts", 10), ("Pav", 1, PCS), ("Farsan & Sev", 10)],
            "Bhel Puri": [("Farsan & Sev", 60), ("Onion", 30), ("Tomato", 20), ("Lemon", 0.25, PCS)],
            "Sev Puri": [("Puri & Chutney Kit", 6, PCS), ("Potato", 50), ("Farsan & Sev", 25)],
            "Pani Puri": [("Puri & Chutney Kit", 6, PCS), ("Potato", 50), ("Kabuli Chana", 20)],
            "Ragda Pattice": [("Potato", 120), ("Green Peas", 60), ("Onion", 20)],
            "Veg Sandwich": [("Sandwich Bread", 3, PCS), ("Potato", 50), ("Tomato", 30), ("Butter", 10)],
            "Cheese Grilled Sandwich": [("Sandwich Bread", 3, PCS), ("Cheese", 40), ("Capsicum", 25), ("Butter", 15)],
            "Veg Burger": [("Burger Buns", 1, PCS), ("Potato", 80), ("Mixed Vegetables", 30), ("Sunflower Oil", 20, ML)],
            "Chicken Burger": [("Burger Buns", 1, PCS), ("Boneless Chicken", 110), ("Maida", 20), ("Sunflower Oil", 25, ML)],
            "French Fries": [("Potato", 200), ("Sunflower Oil", 40, ML)],
            "Veg Frankie": [("Maida", 60), ("Mixed Vegetables", 80), ("Onion", 30), ("Sunflower Oil", 10, ML)],
            "Chicken Frankie": [("Maida", 60), ("Boneless Chicken", 110), ("Onion", 30), ("Sunflower Oil", 10, ML)],
            "Veg Hakka Noodles": [("Hakka Noodles", 110), ("Cabbage & Carrot", 70), ("Soy & Chilli Sauces", 15, ML), ("Sunflower Oil", 20, ML)],
            "Chicken Hakka Noodles": [("Hakka Noodles", 110), ("Boneless Chicken", 100), ("Cabbage & Carrot", 50), ("Soy & Chilli Sauces", 15, ML)],
            "Veg Momos": [("Maida", 70), ("Cabbage & Carrot", 90), ("Garlic", 5)],
        }
        return [(i[0], i[1], i[2] if len(i) > 2 else G) for i in table[name]]

    # ---- Maharashtrian ----
    if cat == "Maharashtrian Dishes":
        table = {
            "Puneri Misal Pav": [("Matki (Moth Beans)", 80), ("Farsan & Sev", 40), ("Pav", 2, PCS), ("Onion", 40), ("Goda Masala", 8), ("Sunflower Oil", 20, ML)],
            "Kolhapuri Misal Pav": [("Matki (Moth Beans)", 80), ("Farsan & Sev", 40), ("Pav", 2, PCS), ("Onion", 40), ("Kolhapuri Masala", 12), ("Sunflower Oil", 25, ML)],
            "Pithla Bhakri": [("Besan (Gram Flour)", 60), ("Jowar Flour", 90), ("Garlic", 6), ("Green Chilli", 8), ("Sunflower Oil", 15, ML)],
            "Zunka Bhakar": [("Besan (Gram Flour)", 70), ("Onion", 60), ("Bajra Flour", 90), ("Sunflower Oil", 20, ML)],
            "Bharli Vangi": [("Brinjal", 200), ("Peanuts", 25), ("Fresh Coconut", 0.25, PCS), ("Goda Masala", 8), ("Sunflower Oil", 25, ML)],
            "Thalipeeth": [("Jowar Flour", 50), ("Besan (Gram Flour)", 30), ("Wheat Flour (Atta)", 30), ("Onion", 40), ("Butter", 10)],
            "Sabudana Khichdi": [("Sabudana", 120), ("Peanuts", 30), ("Potato", 60), ("Ghee", 10)],
            "Kanda Poha": [("Poha", 90), ("Onion", 50), ("Peanuts", 15), ("Sunflower Oil", 15, ML), ("Lemon", 0.25, PCS)],
            "Kothimbir Vadi": [("Coriander Leaves", 60), ("Besan (Gram Flour)", 80), ("Sunflower Oil", 25, ML)],
            "Alu Vadi": [("Colocasia Leaves", 4, PCS), ("Besan (Gram Flour)", 70), ("Jaggery", 10), ("Sunflower Oil", 25, ML)],
            "Shev Bhaji": [("Farsan & Sev", 60), ("Onion", 80), ("Tomato", 60), ("Garlic", 8), ("Sunflower Oil", 25, ML)],
            "Matki Usal": [("Matki (Moth Beans)", 100), ("Onion", 50), ("Fresh Coconut", 0.25, PCS), ("Goda Masala", 8)],
            "Puran Poli": [("Chana Dal", 70), ("Jaggery", 60), ("Wheat Flour (Atta)", 50), ("Ghee", 15)],
            "Varan Bhaat": [("Toor Dal", 60), ("Kolam Rice", 120), ("Ghee", 10), ("Lemon", 0.25, PCS)],
            "Jowar Bhakri with Thecha": [("Jowar Flour", 100), ("Green Chilli", 15), ("Peanuts", 15), ("Garlic", 5)],
            "Masale Bhaat": [("Basmati Rice", 130), ("Mixed Vegetables", 60), ("Goda Masala", 8), ("Cashew Nuts", 8), ("Ghee", 10)],
            "Kombdi Vade": [("Chicken (Curry Cut)", 250), ("Malvani Masala", 12), ("Rice Flour", 80), ("Fresh Coconut", 0.25, PCS), ("Sunflower Oil", 30, ML)],
            "Tambda Pandhra Rassa Thali": [("Mutton (Curry Cut)", 250), ("Kolhapuri Masala", 12), ("Fresh Coconut", 0.25, PCS), ("Jowar Flour", 90), ("Kolam Rice", 100)],
            "Sabudana Vada": [("Sabudana", 80), ("Potato", 60), ("Peanuts", 20), ("Sunflower Oil", 30, ML)],
            "Maharashtrian Veg Thali": [("Mixed Vegetables", 200), ("Toor Dal", 50), ("Wheat Flour (Atta)", 60), ("Jowar Flour", 50), ("Kolam Rice", 120), ("Papad", 1, PCS)],
        }
        return [(i[0], i[1], i[2] if len(i) > 2 else G) for i in table[name]]

    # ---- Starters, mains, seafood: protein + base ----
    if _has(n, "kheema", "keema"):
        add("Chicken Kheema" if "chicken" in n else "Mutton Kheema", 180)
    elif "paya" in n:
        add("Mutton Paya", 250)
    elif "mutton" in n or "laal maas" in n:
        add("Mutton Kheema" if "seekh" in n else "Mutton (Curry Cut)", 220 if "seekh" in n else 250)
    elif _has(n, "tangdi", "lollipop", "wings"):
        add("Chicken Drumsticks & Wings", 280)
    elif "tandoori chicken" in n:
        add("Chicken (Curry Cut)", 350)
    elif "chicken" in n:
        boneless = cat == "Non-Vegetarian Starters" or _has(n, "tikka", "butter chicken", "lababdar", "kheema")
        add("Boneless Chicken" if boneless else "Chicken (Curry Cut)", 220 if boneless else 250)
    elif _has(n, "anda", "egg"):
        add("Eggs", 3, PCS)
    elif "surmai" in n:
        add("Surmai (Kingfish)", 250)
    elif "pomfret" in n:
        add("Pomfret", 300)
    elif "bombil" in n:
        add("Bombil (Bombay Duck)", 250)
    elif "prawn" in n:
        add("Prawns", 200)
    elif "crab" in n:
        add("Crab", 400)
    elif "tisrya" in n:
        add("Tisrya (Clams)", 300)
    elif "rawas" in n:
        add("Rawas (Indian Salmon)", 250)
    elif "bangda" in n:
        add("Bangda (Mackerel)", 250)
    elif "fish" in n:
        add("Fish Fillet (Basa)", 220)
    elif "paneer" in n or "dahi kabab" in n or "kofta" in n:
        add("Paneer", 150 if "paneer" in n else 80)
        if "dahi" in n:
            add("Chakka (Hung Curd)", 120)
    elif "mushroom" in n:
        add("Mushroom", 160)
    elif "corn" in n:
        add("Sweet Corn", 150)
        if "cheese" in n:
            add("Cheese", 40)
    elif _has(n, "gobi", "aloo gobi"):
        add("Cauliflower", 200)
        if "aloo" in n:
            add("Potato", 100)
    elif _has(n, "potato", "aloo"):
        add("Potato", 220)
    elif "bhindi" in n:
        add("Okra (Bhindi)", 200)
    elif "baingan" in n:
        add("Brinjal", 250)
    elif "dal makhani" in n:
        add("Urad Dal (Whole)", 70); add("Butter", 20); add("Fresh Cream", 20, ML)
    elif "dal" in n:
        add("Toor Dal", 80); add("Ghee", 10)
    elif "chana" in n:
        add("Kabuli Chana", 100)
    elif "kaju" in n:
        add("Cashew Nuts", 80)
    elif _has(n, "methi malai matar"):
        add("Green Peas", 120); add("Fenugreek Leaves (Methi)", 40); add("Fresh Cream", 30, ML)
    elif _has(n, "kanda bhaji"):
        add("Onion", 150); add("Besan (Gram Flour)", 70)
    elif "mirchi" in n:
        add("Green Chilli", 80); add("Potato", 80); add("Besan (Gram Flour)", 60)
    elif "papad" in n:
        add("Papad", 1, PCS); add("Onion", 25); add("Tomato", 20)
        return lines
    elif _has(n, "hara bhara"):
        add("Spinach", 80); add("Green Peas", 60); add("Potato", 60)
    else:
        add("Mixed Vegetables", 200)

    # Extra vegetables named in the dish
    if "palak" in n:
        add("Spinach", 150)
    if "methi" in n and "malai matar" not in n:
        add("Fenugreek Leaves (Methi)", 40)
    if _has(n, "kadai", "chilli", "capsicum", "lababdar", "manchurian", "spring roll", "crispy corn"):
        add("Capsicum", 50)
    if _has(n, "matar") and "methi" not in n:
        add("Green Peas", 60)
    if _has(n, "spring roll", "manchurian"):
        add("Cabbage & Carrot", 100); add("Maida", 30)

    # Cooking base
    fried = _has(n, "fry", "65", "pakoda", "koliwada", "crispy", "chilli", "lollipop", "manchurian",
                 "spring roll", "bhaji", "garlic chicken", "honey", "cheese balls", "dahi kabab", "wings")
    tandoor = dish["station"] == "tandoor" or _has(n, "tikka", "tandoori", "kabab", "seekh")
    gravy = cat in ("Vegetarian Main Course", "Chicken Main Course", "Mutton Main Course") or _has(
        n, "curry", "masala", "rassa", "sukka", "thali")

    if tandoor and not gravy:
        add("Curd", 50); add("Red Chilli Powder", 4); add("Lemon", 0.5, PCS)
    if fried:
        add("Sunflower Oil", 40, ML)
        if not tandoor:
            add("Maida", 25)
    if _has(n, "chilli", "manchurian", "garlic chicken", "honey", "hakka"):
        add("Soy & Chilli Sauces", 20, ML)
    if gravy:
        add("Onion", 80); add("Tomato", 60); add("Sunflower Oil", 25, ML); add("Ginger", 6); add("Garlic", 6)
        if _has(n, "kolhapuri", "tambda", "saoji", "sukka", "laal"):
            add("Kolhapuri Masala", 12)
        elif _has(n, "malvani", "goan", "konkan", "surmai curry", "tisrya", "hirwa", "koliwada"):
            add("Malvani Masala", 12); add("Fresh Coconut", 0.25, PCS)
        elif _has(n, "gharguti", "matki"):
            add("Goda Masala", 10)
        else:
            add("Garam Masala", 5)
        if _has(n, "butter", "makhani", "shahi", "malai", "korma", "lababdar", "handi", "afghani", "mughlai", "kofta", "kaju"):
            add("Butter", 15); add("Fresh Cream", 30, ML); add("Cashew Nuts", 10)
        add("Turmeric Powder", 2)
    elif fried or tandoor:
        add("Ginger", 5); add("Garlic", 5)
    if _has(n, "butter garlic"):
        add("Butter", 30); add("Garlic", 15)

    # Merge duplicates (same ingredient added twice)
    merged = {}
    for ing, qty, unit in lines:
        if ing in merged:
            merged[ing] = (ing, merged[ing][1] + qty, unit)
        else:
            merged[ing] = (ing, qty, unit)
    return list(merged.values())
