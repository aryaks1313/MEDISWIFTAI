const API_BASE = "http://127.0.0.1:8000/api";

let token = "";
let currentUser = null;
let medicines = [];
let cart = [];

const $ = (id) => document.getElementById(id);

function setMessage(id, text, isError = false) {
    const element = $(id);
    element.textContent = text;
    element.classList.toggle("error", isError);
}

async function apiRequest(path, options = {}) {
    const headers = options.headers || {};

    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    if (
        options.body &&
        !(options.body instanceof FormData) &&
        !headers["Content-Type"]
    ) {
        headers["Content-Type"] = "application/json";
    }

    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
    });

    const result = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(result.detail || "Request failed");
    }

    return result;
}

function showApplication(user) {
    currentUser = user;
    $("auth-section").classList.add("hidden");
    $("app-section").classList.remove("hidden");

    $("user-name").textContent = user.name;
    $("user-role").textContent = `Role: ${user.role}`;

    loadMedicines();
    loadOrders();
}

function logout() {
    token = "";
    currentUser = null;
    cart = [];

    $("app-section").classList.add("hidden");
    $("auth-section").classList.remove("hidden");
    $("login-password").value = "";
    renderCart();
}

$("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
        const result = await apiRequest("/auth/login", {
            method: "POST",
            body: JSON.stringify({
                email: $("login-email").value.trim(),
                password: $("login-password").value,
            }),
        });

        token = result.access_token;
        showApplication(result.user);
        setMessage("auth-message", "");
    } catch (error) {
        setMessage("auth-message", error.message, true);
    }
});

$("logout-button").addEventListener("click", logout);

$("show-register-button").addEventListener("click", () => {
    $("login-form").classList.add("hidden");
    $("show-register-button").classList.add("hidden");
    $("register-form").classList.remove("hidden");
    setMessage("auth-message", "");
});

$("show-login-button").addEventListener("click", () => {
    $("register-form").classList.add("hidden");
    $("login-form").classList.remove("hidden");
    $("show-register-button").classList.remove("hidden");
    setMessage("auth-message", "");
});

$("register-form").addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
        const result = await apiRequest("/auth/register", {
            method: "POST",
            body: JSON.stringify({
                name: $("register-name").value.trim(),
                email: $("register-email").value.trim(),
                password: $("register-password").value,
                role: $("register-role").value,
            }),
        });

        setMessage(
            "auth-message",
            "Registration successful! Please log in."
        );

        $("register-form").reset();
        $("register-form").classList.add("hidden");
        $("login-form").classList.remove("hidden");
        $("show-register-button").classList.remove("hidden");

        $("login-email").value = result.user.email;
    } catch (error) {
        setMessage("auth-message", error.message, true);
    }
});


async function loadMedicines() {
    try {
        const search = $("medicine-search").value.trim();
        medicines = await apiRequest(
            `/medicines?search=${encodeURIComponent(search)}`
        );

        renderMedicines();
    } catch (error) {
        $("medicine-list").textContent = error.message;
    }
}

function renderMedicines() {
    const container = $("medicine-list");
    container.innerHTML = "";

    if (!medicines.length) {
        container.textContent = "No medicines found.";
        return;
    }

    medicines.forEach((medicine) => {
        const card = document.createElement("div");
        card.className = "medicine-card";

        const title = document.createElement("h3");
        title.textContent = medicine.name;

        const generic = document.createElement("p");
        generic.textContent = `Generic: ${medicine.generic_name}`;

        const price = document.createElement("p");
        price.textContent = `Price: ₹${Number(medicine.price).toFixed(2)}`;

        const stock = document.createElement("p");
        stock.textContent = `Available stock: ${medicine.stock}`;

        const prescription = document.createElement("p");
        prescription.textContent = medicine.requires_prescription
            ? "Prescription required"
            : "No prescription flag";

        const addButton = document.createElement("button");
        addButton.textContent = "Add to cart";
        addButton.disabled = medicine.stock <= 0;
        addButton.addEventListener("click", () => addToCart(medicine.id));

        card.append(
            title,
            generic,
            price,
            stock,
            prescription,
            addButton
        );

        container.appendChild(card);
    });
}

function addToCart(medicineId) {
    const medicine = medicines.find((item) => item.id === medicineId);
    if (!medicine) return;

    const existing = cart.find((item) => item.medicine_id === medicineId);

    if (existing) {
        if (existing.quantity >= medicine.stock) {
            alert("You cannot add more than available stock.");
            return;
        }
        existing.quantity += 1;
    } else {
        cart.push({
            medicine_id: medicine.id,
            name: medicine.name,
            price: Number(medicine.price),
            quantity: 1,
            stock: medicine.stock,
        });
    }

    renderCart();
}

function renderCart() {
    const container = $("cart-list");
    container.innerHTML = "";

    let total = 0;

    cart.forEach((item, index) => {
        total += item.price * item.quantity;

        const row = document.createElement("div");
        row.className = "cart-item";

        const description = document.createElement("span");
        description.textContent =
            `${item.name} — ${item.quantity} × ₹${item.price.toFixed(2)}`;

        const remove = document.createElement("button");
        remove.className = "secondary";
        remove.textContent = "Remove";
        remove.addEventListener("click", () => {
            cart.splice(index, 1);
            renderCart();
        });

        row.append(description, remove);
        container.appendChild(row);
    });

    $("cart-total").textContent = `Total: ₹${total.toFixed(2)}`;
}

$("medicine-search").addEventListener("input", loadMedicines);

$("place-order-button").addEventListener("click", async () => {
    if (!cart.length) {
        setMessage("order-message", "Your cart is empty.", true);
        return;
    }

    const address = $("delivery-address").value.trim();

    if (address.length < 5) {
        setMessage("order-message", "Please enter a delivery address.", true);
        return;
    }

    const prescriptionValue = $("prescription-id").value.trim();

    try {
        const order = await apiRequest("/orders", {
            method: "POST",
            body: JSON.stringify({
                items: cart.map((item) => ({
                    medicine_id: item.medicine_id,
                    quantity: item.quantity,
                })),
                delivery_address: address,
                prescription_id: prescriptionValue
                    ? Number(prescriptionValue)
                    : null,
            }),
        });

        cart = [];
        renderCart();

        setMessage(
            "order-message",
            `Order #${order.id} placed. Status: ${order.status}`
        );

        loadOrders();
        loadMedicines();
    } catch (error) {
        setMessage("order-message", error.message, true);
    }
});

$("prescription-form").addEventListener("submit", async (event) => {
    event.preventDefault();

    const file = $("prescription-file").files[0];

    if (!file) {
        setMessage("prescription-message", "Choose a file first.", true);
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append(
        "preference",
        $("medicine-preference").value
    );

    try {
        const result = await apiRequest("/prescriptions/upload", {
            method: "POST",
            body: formData,
        });

        $("prescription-id").value = result.id;

        setMessage(
            "prescription-message",
            `Prescription uploaded. ID: ${result.id}. ` +
            "It still requires OCR and pharmacist review."
        );
    } catch (error) {
        setMessage("prescription-message", error.message, true);
    }
});

async function loadOrders() {
    try {
        const orders = await apiRequest("/orders");
        const container = $("orders-list");
        container.innerHTML = "";

        if (!orders.length) {
            container.textContent = "No orders yet.";
            return;
        }

        orders.forEach((order) => {
            const row = document.createElement("div");
            row.className = "order-item";

            const heading = document.createElement("strong");
            heading.textContent = `Order #${order.id}`;

            const status = document.createElement("p");
            status.textContent = `Status: ${order.status}`;

            const total = document.createElement("p");
            total.textContent =
                `Total: ₹${Number(order.total_amount).toFixed(2)}`;

            row.append(heading, status, total);
            container.appendChild(row);
        });
    } catch (error) {
        $("orders-list").textContent = error.message;
    }
}

$("refresh-orders-button").addEventListener("click", loadOrders);