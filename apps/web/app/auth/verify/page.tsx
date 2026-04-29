export default function VerifyPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 px-4 py-32">
      <div className="w-full max-w-sm space-y-4 text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-muted text-4xl">
          ✉️
        </div>
        <h1 className="text-2xl font-bold">Vérifiez vos e-mails</h1>
        <p className="text-muted-foreground">
          Si votre adresse e-mail est associée à un compte Greffo, vous recevrez un lien
          de connexion dans quelques secondes.
        </p>
        <p className="text-sm text-muted-foreground">
          Pensez à vérifier vos spams si vous ne voyez rien.
        </p>
      </div>
    </main>
  )
}
