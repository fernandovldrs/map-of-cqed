// Initialize the map and set its view
var map = L.map('map').setView([25.505, -0.09], 2);

// Load and display a tile layer on the map
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// Function to create the custom icon based on an integer
function createCustomIcon(count) {
    return L.divIcon({
        className: 'custom-div-icon', // CSS class for styling
        html: count > 0 
            ? `<div class="icon-circle">+${count}</div>`  // Regular icon with number if count > 0
            : `<div class="icon-circle-small"></div>`,    // Smaller icon if count == 0
        iconSize: count > 0 ? [30, 30] : [15, 15],        // Adjust icon size based on count
        popupAnchor: [0, -10] // Position the popup correctly
    });
}


// Create a marker cluster group
var markers = L.markerClusterGroup({
    iconCreateFunction: function(cluster) {
        // Get markers in the cluster
        var markers = cluster.getAllChildMarkers();
        
        // Calculate the sum of counts for the cluster
        var sum = 0;
        markers.forEach(function(marker) {
            sum += marker.options.count || 0; // Sum the count of all markers in cluster
        });

        // Return a custom icon for the cluster showing the sum
        return L.divIcon({
            html: sum > 0 
                ? `<div class="icon-circle">+${sum}</div>`  // Regular icon with number if count > 0
                : `<div class="icon-circle-small"></div>`,    // Smaller icon if count == 0
            className: 'custom-div-icon', // Custom class for styling
            iconSize: [30, 30]  // Size of the cluster icon
        });
    }
});

// Fetch the research groups data from the local Flask backend
fetch('http://localhost:5000/api/research_groups')
    .then(response => response.json())
    .then(data => {
        data.research_groups.forEach(group => {
            // Create a marker with the custom icon (number + red icon)
            var customIcon = createCustomIcon(group.new_pub_count);

            // Create the marker and add to the marker cluster group
            var marker = L.marker([group.location.latitude, group.location.longitude], { 
                icon: customIcon, 
                count: group.new_pub_count // Store count in marker options for easy access
            });
            marker.bindPopup(createPopupContent(group));
            markers.addLayer(marker); // Add marker to the cluster group
        });

        // Add the marker cluster group to the map
        map.addLayer(markers);
    })
    .catch(error => console.error('Error fetching data:', error));

// Function to create the popup content with group and PI information and a button
function createPopupContent(group) {
    var content = `
        <b>${group.group_name}</b><br> 
        ${group.pi_name}<br>
        ${group.institution_name}<br><br>
        <button onclick="showPublications('${group.group_name}', '${group.group_site}')">See recent publications</button>
    `;
    return content;
}

function showPublications(groupName, groupSite) {
    // Send the groupName to the backend using a POST request
    fetch('http://localhost:5000/api/group_publications_search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ groupname: groupName }) // Send groupName to the backend as 'groupname'
    })
    .then(response => response.json())
    .then(data => {
        var publicationsList = document.getElementById('publicationsList');
        publicationsList.innerHTML = ''; // Clear any existing list items

        // Update the panel title with the group name
        var panelTitle = document.querySelector('#infoPanel h2');
        panelTitle.textContent = `${groupName}`;

        // Add the "Visit group website" link
        var visitLink = document.createElement('p');
        visitLink.innerHTML = `<small><a href="${groupSite}" target="_blank" style="color: #007BFF; text-decoration: none;">Visit group website</a></small>`;

        // Remove any existing link before adding a new one
        var existingLink = panelTitle.nextElementSibling;
        if (existingLink && existingLink.tagName === 'P') {
            existingLink.remove();
        }

        // Insert the visit link just below the title
        panelTitle.insertAdjacentElement('afterend', visitLink);

        // Add new publications section if they exist
        if (Array.isArray(data.new_publications) && data.new_publications.length > 0) {
            var newHeader = document.createElement('h3');
            newHeader.textContent = 'New Publications';
            publicationsList.appendChild(newHeader);

            data.new_publications.forEach(pub => {
                var pubContainer = document.createElement('div');
                pubContainer.style.marginBottom = '15px';

                var listItem = document.createElement('a');
                listItem.href = `https://doi.org/${pub.id}`;
                listItem.textContent = pub.title;
                listItem.target = "_blank";
                listItem.style.fontSize = '16px';
                listItem.style.textDecoration = 'none';
                listItem.style.color = '#000000';

                var metaElement = document.createElement('div');
                metaElement.style.fontSize = '14px';
                metaElement.style.color = 'gray';
                metaElement.style.marginTop = '5px';
                metaElement.textContent = pub.date;

                pubContainer.appendChild(listItem);
                pubContainer.appendChild(metaElement);
                publicationsList.appendChild(pubContainer);
            });
        }

        // Add previous publications section
        if (Array.isArray(data.previous_publications) && data.previous_publications.length > 0) {
            var previousHeader = document.createElement('h3');
            previousHeader.textContent = 'Previous Publications';
            publicationsList.appendChild(previousHeader);

            data.previous_publications.forEach(pub => {
                var pubContainer = document.createElement('div');
                pubContainer.style.marginBottom = '15px';

                var listItem = document.createElement('a');
                listItem.href = `https://doi.org/${pub.id}`;
                listItem.textContent = pub.title;
                listItem.target = "_blank";
                listItem.style.fontSize = '16px';
                listItem.style.textDecoration = 'none';
                listItem.style.color = '#000000';

                var metaElement = document.createElement('div');
                metaElement.style.fontSize = '14px';
                metaElement.style.color = 'gray';
                metaElement.style.marginTop = '5px';
                metaElement.textContent = pub.date;

                pubContainer.appendChild(listItem);
                pubContainer.appendChild(metaElement);
                publicationsList.appendChild(pubContainer);
            });
        }

        // Slide in the panel
        document.getElementById('infoPanel').style.right = '0';
    })
    .catch(error => console.error('Error fetching publications:', error));
}



// Close the panel when the close button is clicked
document.getElementById('closePanel').addEventListener('click', function() {
    document.getElementById('infoPanel').style.right = '-400px';
});
