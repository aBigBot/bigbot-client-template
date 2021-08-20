import datetime
def compute_slots(anchor_date, from_date, to_date, start_time, end_time, duration, interval, number_of_slots):
    result = []
    from_date = datetime.datetime.strptime(from_date, "%Y-%m-%d").date()
    to_date = datetime.datetime.strptime(to_date, "%Y-%m-%d").date()
    anchor_date = datetime.datetime.strptime(anchor_date, "%Y-%m-%d").date()
    start_time = datetime.datetime.strptime(start_time, "%H:%M:%S").time()
    end_time = datetime.datetime.strptime(end_time, "%H:%M:%S").time()

    temp_date = anchor_date
    left = True
    temp_date = anchor_date
    shifter = 1
    while from_date <= to_date:
        temp_slot = 0
        start_datetime = str(temp_date)+" "+str(start_time)
        end_datetime = str(temp_date)+" "+str(end_time)

        datetime_start = datetime.datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
        end = datetime.datetime.strptime(end_datetime, "%Y-%m-%d %H:%M:%S")
        while(datetime_start < end):
            datetime_end = datetime_start + datetime.timedelta(minutes=duration)
            result.append([str(datetime_start), str(datetime_end)])
            datetime_start = datetime_end + datetime.timedelta(minutes=interval)

        from_date += datetime.timedelta(days=1)

        if left and temp_date >= from_date:
            temp_date = anchor_date + datetime.timedelta(days=-shifter)
            left = False
        else:
            if temp_date < to_date:
                temp_date = anchor_date + datetime.timedelta(days=shifter)
                shifter += 1
                left = True

    return result


from_date = str(datetime.date(2020, 10, 10))
to_date = str(datetime.date(2020, 10, 20))
start_time = str(datetime.time(18, 00, 00))
end_time = str(datetime.time(23, 00, 00))
anchor_date = str(datetime.date(2020, 10, 15))

result = compute_slots(anchor_date, from_date, to_date, start_time, end_time,60, 30, 4)
for i in result:
    st = datetime.datetime.strptime(i[0], "%Y-%m-%d %H:%M:%S")
    st = st.strftime("%I:%M %p %d %B %Y")
    ed = datetime.datetime.strptime(i[1], "%Y-%m-%d %H:%M:%S")
    ed = ed.strftime("%I:%M %p %d %B %Y")
    print(st," - ",ed)