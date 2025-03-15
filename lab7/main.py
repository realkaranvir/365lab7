import mysql.connector
import getpass
from datetime import datetime, timedelta
from decimal import Decimal


#db_password = getpass.getpass()

db_password = "Wtr25_365_028415692" # Remove this line before submitting

conn = mysql.connector.connect(user='kasandhu', password=db_password,
                               host='mysql.labthreesixfive.com',
                               database='kasandhu')

cursor = conn.cursor()

def count_weekdays_weekends(start_date, end_date):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    weekdays = 0
    weekends = 0

    while start <= end:
        if start.weekday() < 5:  # Monday to Friday (0-4)
            weekdays += 1
        else:  # Saturday and Sunday (5-6)
            weekends += 1
        start += timedelta(days=1)

    return weekdays, weekends

def rooms_and_rates():
    cursor.execute("""
    SELECT RoomName, ROUND((SUM(DATEDIFF(LEAST(CheckOut, CURDATE()), GREATEST(CheckIn, DATE_SUB(CURDATE(), INTERVAL 180 DAY))))/180),2) AS PopularityScore, MAX(CheckOut) AS NextAvailableCheckIn, 
        (SELECT DATEDIFF(r2.CheckOut, r2.CheckIn) 
        FROM lab7_reservations r2 
        WHERE r2.Room = RoomCode AND r2.CheckOut <= CURDATE() 
        ORDER BY r2.CheckOut DESC 
        LIMIT 1) AS MostRecentStayLength
    FROM lab7_rooms
    JOIN lab7_reservations
    ON RoomCode = Room
    WHERE CheckOut > DATE_SUB(CURDATE(), INTERVAL 180 DAY)
    AND CheckIn < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
    GROUP BY RoomCode
    ORDER BY PopularityScore DESC;
    """)
    result = cursor.fetchall()
    for row in result:
        room_name, popularity, next_available, recent_stay = row
        print(f"\nRoom Name: {room_name}\nPopularity Score: {popularity}\nNext Available: {next_available}\nMost Recent Stay: {recent_stay} days\n")

def cancellation():
    reservation_code = input("Enter reservation code you'd like to cancel: ").strip()
    
    while True:
        confirm = input(f"Confirm you'd like to cancel {reservation_code}? (Y/N): ").strip().lower()
        
        if confirm == "n":
            print("Cancellation aborted.")
            return
        elif confirm == "y":
            try:
                cursor.execute("DELETE FROM lab7_reservations WHERE CODE = %s;", (reservation_code,))
                conn.commit()  
                print(f"Reservation {reservation_code} has been successfully canceled.")
            except mysql.connector.Error as err:
                print(f"Error: {err}")
            return
        else:
            print("Invalid input. Please enter 'Y' for Yes or 'N' for No.")

def detailed_reservation_info():
    print("\nDetailed Reservation Information")
    first_name = input("Enter first name (or leave blank for any): ")
    last_name = input("Enter last name (or leave blank for any): ")
    room_code = input("Enter room code (or leave blank for any): ")
    reservation_code = input("Enter reservation code (or leave blank for any): ")
    start_date = input("Enter start date (YYYY-MM-DD, or leave blank for any): ")
    end_date = input("Enter end date (YYYY-MM-DD, or leave blank for any): ")

    query = """
    SELECT r.CODE, r.FirstName, r.LastName, r.Room, rm.RoomName, r.CheckIn, r.Checkout, 
           r.Kids, r.Adults, rm.bedType, rm.maxOcc, rm.basePrice
    FROM lab7_reservations r
    JOIN lab7_rooms rm ON r.Room = rm.RoomCode
    WHERE 1=1
    """
    
    params = []
    
    if first_name:
        query += " AND r.FirstName LIKE %s"
        params.append(first_name + "%")
    
    if last_name:
        query += " AND r.LastName LIKE %s"
        params.append(last_name + "%")
    
    if room_code:
        query += " AND r.Room LIKE %s"
        params.append(room_code + "%")
    
    if reservation_code:
        query += " AND r.CODE = %s"
        params.append(reservation_code)

    if start_date and end_date:
        query += " AND r.Checkout >= %s AND r.CheckIn <= %s"
        params.append(start_date)
        params.append(end_date)

    
    cursor.execute(query, tuple(params))
    results = cursor.fetchall()

    if results:
        print("\nReservations:")
        for row in results:
            print(f"""
            Reservation Code: {row[0]}
            Guest Name: {row[1]} {row[2]}
            Room: {row[3]} - {row[4]}
            Check-in: {row[5]}
            Check-out: {row[6]}
            Guests: {row[7]} Children, {row[8]} Adults
            Bed Type: {row[9]}
            Max Occupancy: {row[10]}
            Base Price: ${row[11]:.2f}
            """)
    else:
        print("No matching reservations found.")

def reservations():
    first_name = input("Enter first name: ")
    last_name = input("Enter last name: ")
    room_code = input("Enter room code (or 'Any'): ")
    bed_type = input("Enter bed type (or 'Any'): ")
    check_in = input("Enter check in date (YYYY-MM-DD): ")
    check_out = input("Enter check out date (YYYY-MM-DD): ")
    num_children = int(input("Enter number of children: "))
    num_adults = int(input("Enter number of adults: "))

    total_guests = num_children + num_adults

    if check_in > check_out:
        print("Invalid date range")
        return
    
    # Step 1: Query for exact matches
    query = """
    SELECT DISTINCT r.RoomCode, r.RoomName, r.BedType, r.maxOcc, r.basePrice
    FROM lab7_rooms r
    LEFT JOIN lab7_reservations res
    ON r.RoomCode = res.Room
    AND (%s < res.CheckOut AND %s > res.CheckIn)  -- Overlapping reservation check
    WHERE r.maxOcc >= %s
    """

    params = [check_in, check_out, total_guests]

    if bed_type.lower() != "any":
        query += " AND r.BedType = %s"
        params.append(bed_type)

    if room_code.lower() != "any":
        query += " AND r.RoomCode = %s"
        params.append(room_code)

    query += " AND res.Room IS NULL;"  # Ensures no conflicting reservations

    cursor.execute(query, tuple(params))
    result = cursor.fetchall()

    # Step 2: Display available rooms
    if result:
        print("\nAvailable Rooms:")
        for i, row in enumerate(result, start=1):
            print(f"{i}: {row[1]} (Room Code: {row[0]}, Bed Type: {row[2]}, Max Occ: {row[3]})")
        
        # Step 3: Prompt user to select a room
        user_input = input("\nEnter the number of the room you want to book, or enter 'cancel' to cancel: ")
        if user_input.lower() == "cancel":
            print("Reservation cancelled.")
            return

        selection = int(user_input) - 1
        if 0 <= selection < len(result):
            selected_room = result[selection]

            weekdays, weekends = count_weekdays_weekends(check_in, check_out)
            total_cost = (weekdays * selected_room[4]) + (weekends * selected_room[4] * 1.1)

            
            
            # Insert reservation into the database (assuming a reservations table)
            cursor.execute("""
                INSERT INTO lab7_reservations (FirstName, LastName, Room, CheckIn, CheckOut, NumChildren, NumAdults)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (first_name, last_name, selected_room[0], check_in, check_out, num_children, num_adults))
            print(f"""\nBooking confirmed for:
                   First Name: {first_name}
                   Last Name: {last_name}
                   Room Code: {selected_room[0]}
                   Room Name: {selected_room[1]}
                   Bed Type: {selected_room[2]}
                   Check In: {check_in}
                   Check Out: {check_out}
                   Number of Children: {num_children}
                   Number of Adults: {num_adults}
                   Total Cost: ${total_cost:.2f}""")
            print("Reservation successfully made!")
            return
        else:
            print("Invalid selection.")
            return
    else:
        print("\nNo exact matches found.")

    # Step 4: Suggest 5 alternative options based on similarity
    print("\nSearching for alternative options...")

    alt_query = """
    SELECT DISTINCT r.RoomCode, r.RoomName, r.BedType, r.maxOcc, res.CheckIn, res.CheckOut
    FROM lab7_rooms r
    LEFT JOIN lab7_reservations res ON r.RoomCode = res.Room
    WHERE r.maxOcc >= %s
    AND (res.CheckOut <= %s OR res.CheckIn >= %s) -- Ensure no overlap
    ORDER BY ABS(DATEDIFF(res.CheckIn, %s)) -- Prioritize nearby dates
    LIMIT 5;
    """
    cursor.execute(alt_query, (total_guests, check_in, check_out, check_in))
    alt_result = cursor.fetchall()

    if alt_result:
        print("\nAlternative Suggestions:")
        for i, row in enumerate(alt_result, start=1):
            print(f"{i}: {row[1]} (Room Code: {row[0]}, Bed Type: {row[2]}, Max Occ: {row[3]}, Available: {row[4]} to {row[5]})")
    else:
        print("No similar rooms or dates found.")

    # Step 5: Check if the guest count exceeds all room capacities
    cursor.execute("SELECT MAX(maxOcc) FROM lab7_rooms;")
    max_capacity = cursor.fetchone()[0]

    if total_guests > max_capacity:
        print("\nNo suitable rooms available. The requested number of guests exceeds the largest room capacity.")
        
#FR5: Revenue
def revenue():
    # Determine the current calendar year
    current_year = datetime.now().year
    start_of_year = datetime(current_year, 1, 1).date()
    end_of_year = datetime(current_year, 12, 31).date()
    print(f"\nCalculating revenue for the year {current_year}...")

    # Retrieve all rooms with their base price
    cursor.execute("SELECT RoomCode, RoomName, basePrice FROM lab7_rooms;")
    rooms = cursor.fetchall()

    # Initialize revenue data for each room
    room_revenues = {}
    for room in rooms:
        room_code, room_name, base_price = room
        # Ensure base_price is a Decimal
        if not isinstance(base_price, Decimal):
            base_price = Decimal(str(base_price))
        monthly = {m: Decimal('0.0') for m in range(1, 13)}
        room_revenues[room_code] = {
            'name': room_name,
            'base_price': base_price,
            'monthly': monthly,
            'total': Decimal('0.0')
        }

    # Process reservations for each room that overlap the current year
    for room_code in room_revenues:
        cursor.execute("""
            SELECT CheckIn, CheckOut FROM lab7_reservations
            WHERE Room = %s AND CheckOut >= %s AND CheckIn <= %s;
        """, (room_code, start_of_year, end_of_year))
        reservations = cursor.fetchall()
        for res in reservations:
            check_in, check_out = res  # Assumed to be date objects
            # Determine the effective period within the current year
            effective_start = max(check_in, start_of_year)
            # For revenue, count nights from effective_start to the day before effective_end
            effective_end = min(check_out, end_of_year + timedelta(days=1))
            current_date = effective_start
            while current_date < effective_end:
                # Compute revenue for the night (revenue applies for the night of the day)
                if current_date.weekday() < 5:  # Weekday
                    night_revenue = room_revenues[room_code]['base_price']
                else:  # Weekend
                    night_revenue = room_revenues[room_code]['base_price'] * Decimal('1.1')
                # Add revenue for the month corresponding to the night
                month = current_date.month
                room_revenues[room_code]['monthly'][month] += night_revenue
                current_date += timedelta(days=1)

    # Compute total yearly revenue for each room
    for room_code, info in room_revenues.items():
        info['total'] = sum(info['monthly'].values())

    # Compute overall totals for each month across all rooms
    overall_monthly_totals = {m: Decimal('0.0') for m in range(1, 13)}
    overall_total = Decimal('0.0')
    for info in room_revenues.values():
        for m in range(1, 13):
            overall_monthly_totals[m] += info['monthly'][m]
        overall_total += info['total']

    # Print the revenue table with data and dollar signs
    header = f"{'Room':<30}" + ''.join([f"{datetime(current_year, m, 1).strftime('%b'):>10}" for m in range(1, 13)]) + f"{'Total':>10}"
    print(header)
    print('-' * len(header))
    for room_code, info in room_revenues.items():
        row = f"{info['name']:<30}"
        for m in range(1, 13):
            amount = int(round(info['monthly'][m], 0))
            row += f"${amount:9d}"
        total_amount = int(round(info['total'], 0))
        row += f"${total_amount:9d}"
        print(row)
    
    totals_row = f"{'Totals':<30}"
    for m in range(1, 13):
        tot = int(round(overall_monthly_totals[m], 0))
        totals_row += f"${tot:9d}"
    totals_row += f"${int(round(overall_total, 0)):9d}"
    print('-' * len(header))
    print(totals_row)

user_input = ""
while (user_input != "5"):
    print("\nOptions: ")
    print("1. Rooms and Rates")
    print("2. Reservations")
    print("3. Reservation Cancellation")
    print("4. Detailed Reservation Information")
    print("5. Revenue")
    print("6. Exit\n")
    user_input = input("Enter option: ")
    match user_input:
        case "1":
            rooms_and_rates()
        case "2":
            reservations()
        case "3":
            cancellation()
        case "4":
            detailed_reservation_info()
        case "5":
            revenue()
        case "6":
            print("Exiting...")
            break
        case _:
            print("Invalid option")


cursor.close()
conn.close()
