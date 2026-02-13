async function search_endpoint() {

    const input = document.getElementById("searchInput").value;
    
    // EncodeURIComponent allows for spaces, special chars, etc
    const response = await fetch(`/search?str=${encodeURIComponent(input)}`);
    const data = await response.json();
    console.log(data)

    document.getElementById("output").innerText = JSON.stringify(data);
}
