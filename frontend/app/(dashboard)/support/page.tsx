'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { HelpCircle, Mail, MessageSquare, Phone, ExternalLink } from 'lucide-react';
import { useState } from 'react';
import toast from 'react-hot-toast';

export default function SupportPage() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    toast.success('Mensaje enviado correctamente. Le responderemos pronto.');
    setFormData({ name: '', email: '', subject: '', message: '' });
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
          <HelpCircle className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Centro de Soporte</h1>
          <p className="text-muted-foreground">Estamos aquí para ayudarte</p>
        </div>
      </div>

      {/* Contact Methods */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <Mail className="h-8 w-8 text-primary mb-2" />
            <CardTitle className="text-lg">Email</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-2">
              Envíanos un email
            </p>
            <a
              href="mailto:support@uns-hrapp.com"
              className="text-sm text-primary hover:underline flex items-center gap-1"
            >
              support@uns-hrapp.com
              <ExternalLink className="h-3 w-3" />
            </a>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <Phone className="h-8 w-8 text-primary mb-2" />
            <CardTitle className="text-lg">Teléfono</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-2">
              Llámanos de 9:00 a 18:00
            </p>
            <a
              href="tel:+81-3-1234-5678"
              className="text-sm text-primary hover:underline"
            >
              +81-3-1234-5678
            </a>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <MessageSquare className="h-8 w-8 text-primary mb-2" />
            <CardTitle className="text-lg">Chat en Vivo</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-2">
              Chatea con nuestro equipo
            </p>
            <Button variant="outline" size="sm" className="w-full">
              Iniciar Chat
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Contact Form */}
      <Card>
        <CardHeader>
          <CardTitle>Envíanos un Mensaje</CardTitle>
          <CardDescription>
            Completa el formulario y te responderemos en menos de 24 horas
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="name">Nombre</Label>
                <Input
                  id="name"
                  placeholder="Tu nombre completo"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="tu@email.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="subject">Asunto</Label>
              <Input
                id="subject"
                placeholder="¿En qué podemos ayudarte?"
                value={formData.subject}
                onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="message">Mensaje</Label>
              <Textarea
                id="message"
                placeholder="Describe tu problema o pregunta en detalle..."
                rows={6}
                value={formData.message}
                onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                required
              />
            </div>

            <Button type="submit" className="w-full">
              Enviar Mensaje
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* FAQ Section */}
      <Card>
        <CardHeader>
          <CardTitle>Preguntas Frecuentes</CardTitle>
          <CardDescription>Respuestas rápidas a preguntas comunes</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h3 className="font-semibold mb-2">¿Cómo reseteo mi contraseña?</h3>
            <p className="text-sm text-muted-foreground">
              Puedes resetear tu contraseña desde la página de login haciendo clic en
              "¿Olvidaste tu contraseña?" o contactando al administrador del sistema.
            </p>
          </div>

          <div>
            <h3 className="font-semibold mb-2">¿Cómo importo datos de candidatos?</h3>
            <p className="text-sm text-muted-foreground">
              Puedes utilizar la función de importación masiva desde el menú de Candidatos,
              o usar el OCR para escanear 履歴書 (rirekisho) automáticamente.
            </p>
          </div>

          <div>
            <h3 className="font-semibold mb-2">¿El sistema funciona sin conexión?</h3>
            <p className="text-sm text-muted-foreground">
              No, UNS HRApp requiere conexión a internet para funcionar correctamente.
              Todos los datos se almacenan de forma segura en la nube.
            </p>
          </div>

          <div>
            <h3 className="font-semibold mb-2">¿Cómo exporto reportes?</h3>
            <p className="text-sm text-muted-foreground">
              Cada módulo tiene opciones de exportación a PDF y Excel. Busca el botón de
              exportar en la parte superior derecha de cada página.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
