def create_map(key, start_datetime, routes, places, events, colors):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Big Bot Route For Schedule</title>
        <meta charset="utf-8">
        <script src="https://polyfill.io/v3/polyfill.min.js?features=default"></script>
        <style type="text/css">
        #map {{
            height: 100%;
        }}
        html,
        body {{
            height: 100%;
            margin: 0;
            padding: 0;
        }}
        </style>
        <script>
        function initMap() {{
            const startDateTime = "{0}"
            const routes = {1}
            const places = {2}
            const events = {3}
            const colors = {4}
            const map = new google.maps.Map(document.getElementById("map"), {{
            zoom: 13,
            center: places[0]["location"],
            }});
            for (let index = 0; index < routes.length; index++) {{
                const route = new google.maps.Polyline({{
                    path: google.maps.geometry.encoding.decodePath(routes[index]["overview_polyline"]["points"]),
                    geodesic: true,
                    strokeColor: colors[index]["background"],
                    strokeOpacity: 0.8,
                    strokeWeight: 5,
                }})
                route.setMap(map);
            }}
            for (let index = 0; index < places.length; index++) {{
                const marker = addMarker(places[index]["location"], map)
                const dateTime = new Date(startDateTime)
                const date = dateTime.toLocaleDateString()
                if (index === 0) {{
                    const color = "#000"
                    const startTime = dateTime.toLocaleTimeString()
                    const infowindow = new google.maps.InfoWindow({{
                        content: formatInfoWindow("You are here!", places[index]["address"], date, startTime, null, color),
                    }});
                    marker.addListener("click", () => {{
                        infowindow.open(map, marker);
                    }});

                }} else {{
                    const color = colors[index - 1]["background"]
                    console.log(events[index - 1]["start"]["dateTime"])
                    const startTime = new Date(events[index - 1]["start"]["dateTime"]).toLocaleTimeString()
                    const endTime = new Date(events[index - 1]["end"]["dateTime"]).toLocaleTimeString()
                    const infowindow = new google.maps.InfoWindow({{
                        content: formatInfoWindow(events[index - 1]["summary"], places[index]["address"], date, startTime, endTime, color),
                    }});
                    marker.addListener("click", () => {{
                        infowindow.open(map, marker);
                    }});
                }}
            }}
        }}
        function addMarker(location, map) {{
            return new google.maps.Marker({{
            position: location,
            map: map,
            }});
        }}
        function formatInfoWindow(title, address, date, startTime, endTime, color) {{
            return `<h1 style="color: ${{color}}">${{title}}</h1>
                    <div><small>Address: <strong>${{address}}</strong></small></div>
                    <div><small>Date: <strong>${{date}}</strong></small></div>
                    <div><small>Start: <strong>${{startTime}}</strong></small></div>
                    ${{endTime ? `<div><small>End: <strong>${{endTime}}</strong></small></div>` : ''}}`
        }}
        </script>
    </head>
    <body>
        <div id="map"></div>
        <script
        src="https://maps.googleapis.com/maps/api/js?key={5}&callback=initMap&libraries=geometry&v=weekly"
        async
        ></script>
    </body>
    </html>
    """.format(start_datetime, repr(routes), repr(places), repr(events), repr(colors), key)