async function search_endpoint() {
    const response = await fetch("/search");
    const data = await response.json();
    return data;
}
