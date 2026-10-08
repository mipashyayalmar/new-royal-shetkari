"""
Fictional people for the Royal Shetkari demo.

Every name is made up. Customer phone numbers are 10-digit numbers in the
9000100001-9000199999 block, chosen to look obviously sequential; WhatsApp
and SMS receipts stay switched off for the demo restaurant, so nothing is
ever sent to them. Emails use the reserved example.com domain.
"""

# (username, role, first name, last name, monthly salary INR)
STAFF = [
    ("rs_owner", "owner", "Owner", "(Demo)", None),
    ("rs_manager", "manager", "Sachin", "Kale", 32000),
    ("rs_cashier1", "cashier", "Pooja", "Shinde", 18000),
    ("rs_cashier2", "cashier", "Rahul", "Gaikwad", 17000),
    ("rs_captain", "captain", "Nilesh", "Pawar", 20000),
    ("rs_waiter1", "waiter", "Ganesh", "Mane", 14000),
    ("rs_waiter2", "waiter", "Akash", "Bhosale", 14000),
    ("rs_waiter3", "waiter", "Snehal", "Chavan", 13500),
    ("rs_chef1", "chef", "Bhimrao", "Salunkhe", 30000),
    ("rs_chef2", "chef", "Anita", "Lokhande", 24000),
]

FIRST_NAMES = [
    "Aarav", "Aditi", "Ajay", "Akshay", "Amol", "Amruta", "Anand", "Anjali", "Ankita", "Ashwini",
    "Atul", "Bhagyashree", "Chetan", "Deepak", "Dhanashree", "Dinesh", "Gauri", "Harshad", "Hemant",
    "Isha", "Jayant", "Jyoti", "Kalyani", "Kedar", "Ketaki", "Kiran", "Madhura", "Mahesh", "Manasi",
    "Meera", "Milind", "Mrunal", "Nachiket", "Neha", "Nikhil", "Omkar", "Pallavi", "Parag", "Prachi",
    "Pranav", "Prasanna", "Priya", "Rajesh", "Rohan", "Rupali", "Sagar", "Sai", "Sameer", "Sanika",
    "Sanket", "Saurabh", "Shital", "Shreya", "Shubham", "Siddharth", "Sonali", "Suhas", "Sunil",
    "Swapnil", "Tejas", "Trupti", "Tushar", "Uday", "Vaishali", "Varsha", "Vikram", "Vinayak", "Yash",
]
LAST_NAMES = [
    "Apte", "Bapat", "Bhide", "Chitale", "Dalvi", "Deshpande", "Dixit", "Gadgil", "Ghorpade", "Gokhale",
    "Jog", "Joshi", "Kadam", "Karve", "Kelkar", "Khare", "Kulkarni", "Limaye", "Mahajan", "Mhatre",
    "Nadkarni", "Naik", "Oak", "Paranjpe", "Patwardhan", "Phadke", "Rane", "Sathe", "Sawant", "Shirke",
    "Tilak", "Vaidya", "Wagh", "Yadav",
]


def customers(count, rng):
    """`count` fictional customers: (name, phone, email)."""
    seen = set()
    out = []
    n = 0
    while len(out) < count:
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        if (first, last) in seen:
            continue
        seen.add((first, last))
        n += 1
        phone = f"90001{n:05d}"
        email = f"{first.lower()}.{last.lower()}@example.com" if rng.random() < 0.6 else ""
        out.append((f"{first} {last}", phone, email))
    return out


FEEDBACK_COMMENTS = {
    5: ["Kolhapuri mutton was outstanding!", "Best misal in the area.", "Loved the thali, felt like home food.",
        "Quick service and very tasty.", "Biryani was perfect, will come again.", "Excellent sol kadhi."],
    4: ["Good food, slightly slow on a busy evening.", "Tasty, a bit spicy for kids.",
        "Nice ambience, parking is tight.", "Paneer was fresh. Naan could be softer."],
    3: ["Food okay, waited 30 minutes.", "Average experience, AC section was warm."],
    2: ["Order came late and was cold."],
}
