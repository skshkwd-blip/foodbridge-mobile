import { useCallback, useEffect, useState } from "react";
import {
  Alert, FlatList, Image, Platform, Pressable, RefreshControl, SafeAreaView,
  ScrollView, StatusBar, StyleSheet, Switch, Text, TextInput, View,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as ImagePicker from "expo-image-picker";

// Your PythonAnywhere address, https, no trailing slash
const BASE = "https://YOURUSERNAME.pythonanywhere.com";

const C = { ink: "#1F2A24", leaf: "#2F6B4F", paper: "#FAFAF7", line: "#DDE3DC", bad: "#B3402A", gold: "#B7791F" };

async function call(path, token, method = "GET", body) {
  const res = await fetch(BASE + path, {
    method,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Something went wrong. Try again.");
  return data;
}

// multipart upload (photos). Do not set Content-Type: fetch adds the boundary itself.
async function upload(path, token, fields, photos) {
  const form = new FormData();
  Object.entries(fields).forEach(([k, v]) => form.append(k, v));
  Object.entries(photos).forEach(([k, uri]) => form.append(k, { uri, name: `${k}.jpg`, type: "image/jpeg" }));
  const res = await fetch(BASE + path, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Upload failed. Try again.");
  return data;
}

const Button = ({ label, onPress, ghost }) => (
  <Pressable onPress={onPress} style={[s.btn, ghost && { backgroundColor: "transparent" }]}>
    <Text style={[s.btnText, ghost && { color: C.leaf }]}>{label}</Text>
  </Pressable>
);
const Field = (p) => <TextInput placeholderTextColor="#8A968E" autoCapitalize="none" style={s.input} {...p} />;
const Badge = ({ ok, yes, no }) => (
  <Text style={[s.badge, { color: ok ? C.leaf : C.gold, borderColor: ok ? C.leaf : C.gold }]}>{ok ? yes : no}</Text>
);
const is = (v, x) => String(v || "").toLowerCase() === x;

const act = async (token, path, method, body, reload, msg) => {
  try {
    const r = await call(path, token, method, body);
    if (msg) Alert.alert(msg(r));
  } catch (e) { Alert.alert("Couldn't do that", e.message); }
  reload();
};

/* ---------- cards ---------- */

const DonorCard = ({ item, token, reload }) => (
  <View style={s.card}>
    <Text style={s.title}>{item.food_type} · {item.quantity}</Text>
    <Text style={s.meta}>Status: {item.donation_status}</Text>
    {item.ngo_name && <Text style={s.meta}>NGO: {item.ngo_name}</Text>}
    {item.volunteer_name && (
      <View style={s.idCard}>
        <Image
          source={{ uri: `${BASE}/api/verify/photo/${item.donation_id}`, headers: { Authorization: `Bearer ${token}` } }}
          style={s.avatar}
        />
        <View style={{ flex: 1, gap: 2 }}>
          <Text style={s.title}>{item.volunteer_name}</Text>
          <Badge ok={item.volunteer_verified} yes="ID verified" no="Not verified" />
          {item.volunteer_vehicle ? <Text style={s.meta}>Vehicle: {item.volunteer_vehicle}</Text> : null}
          {item.volunteer_contact ? <Text style={s.meta}>{item.volunteer_contact}</Text> : null}
        </View>
      </View>
    )}
    {item.otp_code && !is(item.donation_status, "completed") && (
      <Text style={s.hot}>Pickup code: {item.otp_code} (tell it only to the verified volunteer)</Text>
    )}
    {is(item.donation_status, "pending") &&
      <Button ghost label="Withdraw this listing" onPress={() => act(token, `/api/donations/${item.donation_id}`, "DELETE", null, reload)} />}
  </View>
);

const NgoOpenCard = ({ item, token, reload }) => {
  const [qty, setQty] = useState(String(item.quantity));
  return (
    <View style={s.card}>
      <Text style={s.title}>{item.food_type} · {item.quantity} available</Text>
      <Badge ok={item.donor_verified} yes="FSSAI verified donor" no="Donor licence not verified" />
      <Text style={s.meta}>{item.is_veg === 0 ? "Non-veg" : "Veg"}{item.cooked_at ? ` · cooked at ${item.cooked_at}` : ""}</Text>
      <Text style={s.meta}>{item.donor_name} · {item.donor_address || "No address"}</Text>
      <Text style={s.meta}>{item.date_of_donation} until {item.time || "any time"} · hygiene {item.donor_rating}/5</Text>
      <Field placeholder="How many can you take?" keyboardType="number-pad" value={qty} onChangeText={setQty} />
      <Button label="Accept" onPress={() => act(token, "/api/ngo/accept-donation", "POST",
        { donation_id: item.donation_id, accepted_qty: qty }, reload, (r) => r.message)} />
    </View>
  );
};

const NgoOrderCard = ({ item, token, reload }) => (
  <View style={s.card}>
    <Text style={s.title}>{item.food_type} · {item.quantity}</Text>
    <Text style={s.meta}>From {item.donor_name}</Text>
    <Text style={s.meta}>Delivery: {item.delivery_status} · Volunteer: {item.volunteer_name || "not assigned yet"}</Text>
    {!is(item.delivery_status, "delivered") && item.volunteer_name &&
      <Button label="Mark as received" onPress={() => act(token, "/api/ngo/mark-received", "POST",
        { delivery_id: item.delivery_id, pickup_id: item.pickup_id }, reload)} />}
  </View>
);

const VolOpenCard = ({ item, token, reload }) => (
  <View style={s.card}>
    <Text style={s.title}>{item.food_type} · {item.quantity}</Text>
    <Text style={s.meta}>Pick up: {item.donor_name}, {item.donor_address || "No address"}</Text>
    <Text style={s.meta}>Deliver to: {item.ngo_name}, {item.ngo_address || "No address"}</Text>
    <Button label="Take this pickup" onPress={() => act(token, "/api/volunteer/accept-assignment", "POST",
      { pickup_id: item.pickup_id }, reload, (r) => r.message)} />
  </View>
);

const VolMineCard = ({ item, token, reload }) => {
  const [otp, setOtp] = useState("");
  const done = is(item.status, "delivered");
  const started = is(item.status, "in progress");
  const send = (status) => act(token, "/api/volunteer/update-pickup", "POST", { pickup_id: item.pickup_id, status, otp }, reload);
  return (
    <View style={s.card}>
      <Text style={s.title}>{item.food_type} · {item.quantity}</Text>
      <Text style={s.meta}>Pick up: {item.donor_name}, {item.donor_address || "No address"} {item.donor_contact || ""}</Text>
      <Text style={s.meta}>Deliver to: {item.ngo_name}, {item.ngo_address || "No address"} {item.ngo_contact || ""}</Text>
      <Text style={s.meta}>Status: {item.status}</Text>
      {!done && !started && <Button label="Start pickup" onPress={() => send("In Progress")} />}
      {started && (
        <>
          <Field placeholder="Code from the donor" keyboardType="number-pad" value={otp} onChangeText={setOtp} />
          <Button label="Confirm delivery" onPress={() => send("Delivered")} />
        </>
      )}
    </View>
  );
};

/* ---------- verification screen ---------- */

const VERIFY = {
  donor: {
    intro: "Businesses (restaurants, caterers, hotels) should add their FSSAI licence. Individuals can skip this.",
    texts: [["fssai_no", "FSSAI licence number (14 digits)", "number-pad"]],
    photos: [["license_file", "Photo of FSSAI certificate", false]],
  },
  ngo: {
    intro: "Your NGO must be verified before it can accept food.",
    texts: [["darpan_id", "NGO Darpan unique ID"], ["contact_person", "Contact person's name"]],
    photos: [["reg_file", "Photo of registration certificate (Trust / Society / Section 8)", false]],
  },
  volunteer: {
    intro: "You must be verified before taking pickups. Donors will see your photo and vehicle number.",
    texts: [["vehicle_no", "Vehicle number (or type 'none')"], ["emergency_contact", "Emergency contact number", "phone-pad"]],
    photos: [["id_file", "Photo ID (driving licence, college ID or voter ID)", false], ["selfie_file", "Selfie", true]],
  },
};

function VerifyScreen({ session, onChanged }) {
  const cfg = VERIFY[session.user.role];
  const [status, setStatus] = useState(null);
  const [vals, setVals] = useState({});
  const [pics, setPics] = useState({});

  useEffect(() => { call("/api/verify/me", session.token).then(setStatus).catch(() => {}); }, []);

  const pick = async (key, camera) => {
    if (camera) {
      const p = await ImagePicker.requestCameraPermissionsAsync();
      if (!p.granted) return Alert.alert("Camera needed", "Allow camera access to take a selfie.");
    }
    const r = await (camera ? ImagePicker.launchCameraAsync : ImagePicker.launchImageLibraryAsync)({ quality: 0.5 });
    if (!r.canceled) setPics({ ...pics, [key]: r.assets[0].uri });
  };

  const submit = async () => {
    try {
      await upload("/api/verify/submit", session.token, vals, pics);
      Alert.alert("Submitted", "An admin will review your documents.");
      setStatus({ ...status, status: "Pending" });
      onChanged();
    } catch (e) { Alert.alert("Couldn't submit", e.message); }
  };

  const st = status?.status || "None";
  const color = st === "Verified" ? C.leaf : st === "Rejected" ? C.bad : C.gold;
  return (
    <ScrollView contentContainerStyle={{ padding: 20, gap: 12 }}>
      <Text style={[s.title, { color }]}>Status: {st === "None" ? "Not submitted" : st}</Text>
      <Text style={s.meta}>{cfg.intro}</Text>
      {st === "Verified" ? <Text style={s.meta}>You're all set. To change your documents, submit again and an admin will re-check them.</Text> : null}
      {cfg.texts.map(([k, label, kb]) => (
        <Field key={k} placeholder={label} keyboardType={kb} value={vals[k] ?? status?.[k] ?? ""} onChangeText={(v) => setVals({ ...vals, [k]: v })} />
      ))}
      {cfg.photos.map(([k, label, camera]) => (
        <View key={k} style={{ gap: 6 }}>
          <Button ghost label={pics[k] ? `Change: ${label}` : label} onPress={() => pick(k, camera)} />
          {pics[k] && <Image source={{ uri: pics[k] }} style={{ height: 140, borderRadius: 10 }} resizeMode="cover" />}
        </View>
      ))}
      <Button label={st === "None" ? "Submit for verification" : "Submit again"} onPress={submit} />
    </ScrollView>
  );
}

/* ---------- tabs per role ---------- */

const TABS = {
  donor: [
    { label: "My food", path: "/api/donor/donations", pick: (r) => r.data, Card: DonorCard },
    { label: "Donate", form: "donate" },
    { label: "Verify", form: "verify" },
  ],
  ngo: [
    { label: "Available", path: "/api/ngo/available-donations", pick: (r) => r.data, Card: NgoOpenCard },
    { label: "Orders", path: "/api/ngo/orders", pick: (r) => r.data, Card: NgoOrderCard },
    { label: "Verify", form: "verify" },
  ],
  volunteer: [
    { label: "Open", path: "/api/volunteer/pickups", pick: (r) => r.available, Card: VolOpenCard },
    { label: "Mine", path: "/api/volunteer/pickups", pick: (r) => r.data, Card: VolMineCard },
    { label: "Verify", form: "verify" },
  ],
};

function Feed({ tab, token }) {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    setBusy(true);
    try { setItems(tab.pick(await call(tab.path, token)) || []); }
    catch (e) { Alert.alert("Couldn't load", e.message); }
    setBusy(false);
  }, [tab, token]);
  useEffect(() => { load(); }, [load]);
  return (
    <FlatList
      data={items}
      keyExtractor={(x, i) => String(x.donation_id ?? x.pickup_id ?? x.delivery_id ?? i)}
      refreshControl={<RefreshControl refreshing={busy} onRefresh={load} />}
      contentContainerStyle={{ padding: 16, gap: 12 }}
      ListEmptyComponent={<Text style={s.meta}>Nothing here yet. Pull down to refresh.</Text>}
      renderItem={({ item }) => <tab.Card item={item} token={token} reload={load} />}
    />
  );
}

function DonateForm({ token, onDone }) {
  const [f, setF] = useState({ food_type: "", quantity: "", date_of_donation: new Date().toISOString().slice(0, 10), time: "", cooked_at: "", is_veg: true });
  const set = (k) => (v) => setF({ ...f, [k]: v });
  const submit = async () => {
    try { await call("/api/donations", token, "POST", f); Alert.alert("Listed", "NGOs can now see your food."); onDone(); }
    catch (e) { Alert.alert("Couldn't list food", e.message); }
  };
  return (
    <ScrollView contentContainerStyle={s.pad}>
      <Field placeholder="What food is it?" value={f.food_type} onChangeText={set("food_type")} autoCapitalize="sentences" />
      <Field placeholder="Quantity (number of meals)" keyboardType="number-pad" value={f.quantity} onChangeText={set("quantity")} />
      <Field placeholder="Date (YYYY-MM-DD)" value={f.date_of_donation} onChangeText={set("date_of_donation")} />
      <Field placeholder="Cooked at (HH:MM, 24-hour)" value={f.cooked_at} onChangeText={set("cooked_at")} />
      <Field placeholder="Available until (HH:MM, 24-hour)" value={f.time} onChangeText={set("time")} />
      <View style={s.row}>
        <Text style={{ color: C.ink, flex: 1, alignSelf: "center" }}>{f.is_veg ? "Vegetarian" : "Non-vegetarian"}</Text>
        <Switch value={f.is_veg} onValueChange={set("is_veg")} trackColor={{ true: C.leaf }} />
      </View>
      <Button label="List this food" onPress={submit} />
    </ScrollView>
  );
}

function AuthScreen({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ role: "donor", name: "", email: "", mobile: "", password: "" });
  const set = (k) => (v) => setF({ ...f, [k]: v });
  const submit = async () => {
    try { onAuth(await call(mode === "login" ? "/api/auth/login" : "/api/auth/signup", null, "POST", f)); }
    catch (e) { Alert.alert("Couldn't continue", e.message); }
  };
  return (
    <View style={s.pad}>
      <Text style={s.brand}>FoodBridge</Text>
      <Text style={s.meta}>Surplus food, to the people who need it.</Text>
      <View style={s.row}>
        {[["donor", "Donor"], ["ngo", "NGO"], ["volunteer", "Volunteer"]].map(([r, l]) => (
          <Pressable key={r} onPress={() => set("role")(r)} style={[s.chip, f.role === r && s.chipOn]}>
            <Text style={{ color: f.role === r ? "#fff" : C.ink }}>{l}</Text>
          </Pressable>
        ))}
      </View>
      <Field placeholder={f.role === "donor" ? "Your name" : "Name of your NGO or volunteer name"} value={f.name} onChangeText={set("name")} autoCapitalize="words" />
      {mode === "signup" && <Field placeholder="Email" keyboardType="email-address" value={f.email} onChangeText={set("email")} />}
      {mode === "signup" && <Field placeholder="Mobile number" keyboardType="phone-pad" value={f.mobile} onChangeText={set("mobile")} />}
      <Field placeholder="Password" secureTextEntry value={f.password} onChangeText={set("password")} />
      <Button label={mode === "login" ? "Log in" : "Create account"} onPress={submit} />
      <Button ghost label={mode === "login" ? "New here? Create an account" : "Have an account? Log in"}
        onPress={() => setMode(mode === "login" ? "signup" : "login")} />
    </View>
  );
}

export default function App() {
  const [session, setSession] = useState(null);
  const [ready, setReady] = useState(false);
  const [tabIdx, setTabIdx] = useState(0);
  const [vstatus, setVstatus] = useState("None");

  const refreshStatus = useCallback((sess) => {
    if (!sess) return;
    call("/api/verify/me", sess.token).then((r) => setVstatus(r.status)).catch(() => {});
  }, []);

  useEffect(() => {
    AsyncStorage.getItem("session").then((v) => {
      if (v) { const x = JSON.parse(v); setSession(x); refreshStatus(x); }
      setReady(true);
    });
  }, [refreshStatus]);

  const onAuth = async (x) => {
    await AsyncStorage.setItem("session", JSON.stringify(x));
    setTabIdx(0); setSession(x); refreshStatus(x);
  };
  const logout = async () => { await AsyncStorage.removeItem("session"); setSession(null); setVstatus("None"); };

  if (!ready) return null;
  const tabs = session ? TABS[session.user.role] : [];
  const tab = tabs[tabIdx];
  const needsVerify = session && session.user.role !== "donor" && vstatus !== "Verified";

  return (
    <SafeAreaView style={s.screen}>
      {!session ? <AuthScreen onAuth={onAuth} /> : (
        <>
          <View style={s.header}>
            <Text style={s.headerTitle}>{session.user.name}</Text>
            <Pressable onPress={logout}><Text style={{ color: "#fff" }}>Log out</Text></Pressable>
          </View>
          {needsVerify && (
            <Pressable style={s.banner} onPress={() => setTabIdx(tabs.length - 1)}>
              <Text style={{ color: C.ink }}>
                {vstatus === "Pending" ? "Verification is being reviewed." : vstatus === "Rejected" ? "Verification was rejected. Tap to submit again." : "Verify your account to start. Tap here."}
              </Text>
            </Pressable>
          )}
          <View style={{ flex: 1 }}>
            {tab.form === "donate" ? <DonateForm token={session.token} onDone={() => setTabIdx(0)} />
              : tab.form === "verify" ? <VerifyScreen session={session} onChanged={() => refreshStatus(session)} />
              : <Feed key={tab.label} tab={tab} token={session.token} />}
          </View>
          <View style={s.tabs}>
            {tabs.map((t, i) => (
              <Pressable key={t.label} style={s.tab} onPress={() => setTabIdx(i)}>
                <Text style={i === tabIdx && s.tabOn}>{t.label}</Text>
              </Pressable>
            ))}
          </View>
        </>
      )}
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: C.paper, paddingTop: Platform.OS === "android" ? StatusBar.currentHeight : 0 },
  pad: { padding: 24, gap: 12, flexGrow: 1, justifyContent: "center" },
  brand: { fontSize: 34, fontWeight: "800", color: C.leaf },
  input: { borderWidth: 1, borderColor: C.line, backgroundColor: "#fff", borderRadius: 10, padding: 14, fontSize: 16, color: C.ink },
  btn: { backgroundColor: C.leaf, borderRadius: 10, padding: 14, alignItems: "center" },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 16, textAlign: "center" },
  row: { flexDirection: "row", gap: 8 },
  chip: { flex: 1, padding: 12, borderRadius: 10, borderWidth: 1, borderColor: C.line, alignItems: "center", backgroundColor: "#fff" },
  chipOn: { backgroundColor: C.leaf, borderColor: C.leaf },
  header: { backgroundColor: C.leaf, padding: 16, flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  headerTitle: { color: "#fff", fontSize: 20, fontWeight: "700" },
  banner: { backgroundColor: "#FBEFD5", padding: 12 },
  card: { backgroundColor: "#fff", borderRadius: 12, padding: 16, gap: 6, borderWidth: 1, borderColor: C.line },
  title: { fontSize: 18, fontWeight: "700", color: C.ink },
  meta: { color: C.ink, opacity: 0.7 },
  hot: { color: C.bad, fontWeight: "700", fontSize: 16 },
  badge: { alignSelf: "flex-start", borderWidth: 1, borderRadius: 20, paddingHorizontal: 10, paddingVertical: 2, fontSize: 12, fontWeight: "700" },
  idCard: { flexDirection: "row", gap: 12, borderWidth: 1, borderColor: C.line, borderRadius: 10, padding: 10, backgroundColor: C.paper },
  avatar: { width: 64, height: 64, borderRadius: 32, backgroundColor: C.line },
  tabs: { flexDirection: "row", borderTopWidth: 1, borderColor: C.line, backgroundColor: "#fff" },
  tab: { flex: 1, padding: 16, alignItems: "center" },
  tabOn: { color: C.leaf, fontWeight: "800" },
});
