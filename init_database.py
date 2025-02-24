from models import *
from decimal import Decimal

def init_database():
    # Create tables
    db.connect()
    db.drop_tables([Customer, Item, Order, OrderItem])
    db.create_tables([Customer, Item, Order, OrderItem])
    
    # Initialize customers
    customers = [
        "AEB SE",
        "Augustenstüble",
        "BENZ & CO. Gastronomie GmbH",
        "Bo's UG haftungsbeschränkt",
        "Brick House GbR",
        "Claudia Kiebele & Georg Bayer",
        "E. Breuninger GmbH & Co.",
        "Fabio Di Tommaso",
        "FAM-Consulting",
        "Feinkost Böhm GmbH",
        "Feuilleton GmbH",
        "Frau Katharina Bretsch",
        "Frau Nadja Prokhorenko",
        "Gast KG",
        "Geco Gardens, Dr. Bastian Winkler",
        "Geco Gardens GmbH",
        "Goldener Adler",
        "Heldmann GmbH & Co. KG",
        "Hotel zur Weinsteige GmbH Restaurant am Wallgraben",
        "Jimis Gastronomie GmbH",
        "Keimgrün GmbH",
        "Keltenhof Frischprodukte GmbGH",
        "Kommunikationsbüro Ulmer GmbH",
        "La Casa del Gusto",
        "LBBW Gastro Event GmbH",
        "Mat Drycker GmbH",
        "Möhringer Hexle",
        "Netzer",
        "OBI GmbH & Co. Deutschland KG",
        "Pier 51 Restaurant GmbH & Co. KG",
        "Porsche Museum",
        "Restaurant Schillerhöhe GmbH",
        "Ritzi Stuttgart GmbH & Co. KG",
        "Ruthenberg&Schlatter GbR",
        "Saatzucht Bardowick GmbH",
        "Schönbuch-Bräu Betriebs-GmbH",
        "Schweizers Restaurant",
        "Speisemeisterei Stuttgart GmbH",
        "Staiger GmbH",
        "The Gardener's Nosh GmbH",
        "Universität Hohenheim, Geschäftsstelle Bioökonomie Hohenheim",
        "Urban Concept GmbH",
        "vhy! GmbH",
        "Waldhotel Stuttgart GmbH",
        "Weltcafé",
        "Wielandshöhe",
        "ZEDO GmbH",
        "Zheyu Century GmbH",
        "Leibspeise",
        "Vector",
        "Ludwig",
        "Mozzarella Bar",
        "Vegalena",
        "Café Lesbar",
        "Vector Energetic",
        "New Josch",
        "Chobab",
        "Hommage",
        "Kaiserbau",
        "Waldhorn",
        "Dinkelacker",
        "Probe",
        "Mezzeria",
        "Öttinger",
        "Leon",
        "Hardts",
        "Zum Ackerbürger",
        "Schwanen Hotel",
        "Maerz Bietigheim",
        "Holz & Feuer",
        "Veganes Gold",
        "Le Meridien",
        "Felix",
        "Kaleya",
        "Auszeit (ohne Lieferschein)",
        "Krehl's",
        "Linde",
        "Nödinger Gastro GmbH",
        "Better Taste",
        "Bachofer",
        "Brunner",
        "Cervus",
        "Weisser Ochse",
        "Danza",
        "Fraunhofer",
        "Brauhaus zum Schwanen",
        "Schlegel",
        "Katharina Pilze"
    ]
    
    for customer_name in customers:
        Customer.create(name=customer_name)

    # Initialize items
    items_data = [
        ("Alfalfa", 15, 4, 3, 7, 22.90, "Hanf"),
        ("Amaranth", 10, 5, 3, 8, 22.90, "Hanf"),
        ("Anis", 15, 9, 7, 16, 22.90, "Hanf"),
        ("Basilikum", 15, 7, 6, 13, 22.90, "Hanf"),
        ("Brokkoli", 15, 4, 3, 7, 22.90, "Hanf"),
        ("Buchweizen", 45, 12, 5, 4, 22.90, "Hanf"),
        ("Dill", 10, 8, 4, 12, 22.90, "Hanf"),
        ("Erbse", 70, 12, 6, 7, 22.90, "Hanf"),
        ("Grünkohl", 15, 4, 5, 9, 22.90, "Hanf"),
        ("Hafer", 45, 4, 4, 8, 16.90, "Hanf"),
        ("Kapuzinerkresse", 65, 12, 8, 7, 22.90, "Cellulose"),
        ("Kohlrabi Rot", 15, 6, 3, 9, 22.90, "Hanf"),
        ("Komazuna", 15, 4, 3, 7, 22.90, "Hanf"),
        ("Koriander", 25, 8, 6, 14, 22.90, "Cellulose"),
        ("Mais", 120, 12, 10, 0, 22.90, "Hanf"),
        ("Möhre", 15, 8, 5, 13, 22.90, "Hanf"),
        ("Mungobohne", 45, 12, 5, 6, 22.90, "Hanf"),
        ("Petersilie", 20, 9, 7, 16, 22.90, "Cellulose"),
        ("Radieschen", 15, 4, 3, 7, 15.90, "Hanf"),
        ("Rettich", 15, 4, 3, 7, 15.90, "Hanf"),
        ("R & R", 15, 4, 3, 7, 16.90, "Hanf"),
        ("Rotkohl", 15, 4, 5, 9, 22.90, "Hanf"),
        ("Rucola", 10, 4, 3, 7, 22.90, "Hanf"),
        ("Rote Radieschen", 25, 5, 3, 8, 16.90, "Hanf"),
        ("Schnittknoblauch", 30, 5, 6, 11, 22.90, "Cellulose"),
        ("Sellerie", 10, 9, 5, 14, 22.90, "Hanf"),
        ("Senf", 15, 3, 3, 6, 16.90, "Hanf"),
        ("Red Giant Senf", 15, 4, 4, 8, 22.90, "Hanf"),
        ("Sonnenblume", 45, 12, 6, 5, 22.90, "Hanf"),
        ("Tagetes", 15, 6, 4, 10, 22.90, "Hanf"),
        ("Weizengras", 45, 4, 4, 8, 16.90, "Hanf"),
        ("Mitzuna", 15, 4, 3, 7, 22.90, "Hanf"),
        ("Zitronenbasilikum", 15, 8, 6, 14, 22.90, "Hanf"),
        ("pompom", 0, 15, 15, 30, 30.00, None)
    ]
    
    for item in items_data:
        Item.create(
            name=item[0],
            seed_quantity=item[1],
            soaking_days=item[2],
            germination_days=item[3],
            growth_days=item[4],
            price=item[5],
            substrate=item[6]
        )
    
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database()