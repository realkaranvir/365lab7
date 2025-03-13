import mysql.connector
import getpass
from datetime import datetime, timedelta


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
            print("Reservation Cancellation")
        case "4":
            print("Detailed Reservation Information")
        case "5":
            print("Revenue")
        case "6":
            print("Exiting...")
            break
        case _:
            print("Invalid option")


cursor.close()
conn.close()

