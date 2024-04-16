import Cookies from "js-cookie";
import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { API_URL, COOKIE_ATTRS } from "../../constants";
import styles from "./login.module.css";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    if (Cookies.get("token")) {
      navigate("/");
    }
  }, []);

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();

    try {
      const formData = new FormData();
      formData.append("username", username);
      formData.append("password", password);

      const response = await fetch(`${API_URL}/users/login`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        Cookies.set("token", data.access_token, COOKIE_ATTRS);
        navigate("/");
      } else {
        toast.error(data.detail);
      }
    } catch (error) {
      toast.error("Network error, please try again later");
    }
  };
  return (
    <form onSubmit={handleLogin} className={styles.loginForm}>
      <input
        type="text"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        className={styles.loginInput}
        placeholder="Username"
      />
      <input
        type="password"
        value={password}
        className={styles.loginInput}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
      />
      <button type="submit">Log in</button>
    </form>
  );
}
